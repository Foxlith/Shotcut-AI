/*
 * Copyright (c) 2026 Meltytech, LLC
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "aitools.h"

#include "Logger.h"
#include "actions.h"
#include "controllers/filtercontroller.h"
#include "docks/playlistdock.h"
#include "docks/timelinedock.h"
#include "mainwindow.h"
#include "mltcontroller.h"
#include "models/attachedfiltersmodel.h"
#include "models/metadatamodel.h"
#include "models/multitrackmodel.h"
#include "models/playlistmodel.h"
#include "player.h"
#include "proxymanager.h"
#include "qmltypes/qmlfilter.h"
#include "qmltypes/qmlmetadata.h"
#include "settings.h"
#include "shotcut_mlt_properties.h"
#include "util.h"
#include "videowidget.h"

#include <cmath>
#include <memory>
#include <QAction>
#include <QBuffer>
#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QHash>
#include <QImage>
#include <QJsonArray>
#include <QJsonDocument>
#include <QScopedValueRollback>
#include <QSet>
#include <QUndoStack>
#include <QUuid>

namespace {

// ---------------------------------------------------------------------------------------
// Time: the tools take seconds or a timecode and answer in seconds and frames.

double framesPerSecond()
{
    const double fps = MLT.profile().fps();
    return fps > 0.0 ? fps : 25.0;
}

double round3(double value)
{
    return std::round(value * 1000.0) / 1000.0;
}

double secondsOf(int frames)
{
    return round3(frames / framesPerSecond());
}

QString timecodeOf(int frames)
{
    qint64 ms = qRound64(qMax(0, frames) * 1000.0 / framesPerSecond());
    const qint64 hours = ms / 3600000;
    ms %= 3600000;
    const qint64 minutes = ms / 60000;
    ms %= 60000;
    const qint64 seconds = ms / 1000;
    ms %= 1000;
    return QString::asprintf("%02lld:%02lld:%02lld.%03lld", hours, minutes, seconds, ms);
}

QJsonObject timeJson(int frames)
{
    return QJsonObject{{"seconds", secondsOf(frames)},
                       {"frames", frames},
                       {"timecode", timecodeOf(frames)}};
}

const char *kTimeHelp = "seconds (number) or a timecode such as \"00:01:02.500\", \"01:02.5\", "
                        "\"00:01:02:12\" (hours:minutes:seconds:frames) or \"120f\" (frames)";

/// Parses a time argument into frames.
bool parseTime(const QJsonValue &value, int &frames, QString &error, bool allowNegative = false)
{
    double seconds = 0.0;
    if (value.isDouble()) {
        seconds = value.toDouble();
    } else if (value.isString()) {
        auto text = value.toString().trimmed();
        bool ok = false;
        if (text.endsWith(QLatin1Char('f'), Qt::CaseInsensitive)) {
            frames = text.chopped(1).trimmed().toInt(&ok);
            if (ok && (allowNegative || frames >= 0))
                return true;
            error = QStringLiteral("Invalid frame count \"%1\"").arg(value.toString());
            return false;
        }
        const bool negative = text.startsWith(QLatin1Char('-'));
        if (negative)
            text = text.mid(1);
        const auto parts = text.split(QLatin1Char(':'));
        if (parts.size() == 4) {
            // SMPTE-like hours:minutes:seconds:frames
            double total = 0.0;
            for (int i = 0; i < 3; ++i) {
                total = total * 60.0 + parts.at(i).toDouble(&ok);
                if (!ok)
                    break;
            }
            const int extraFrames = parts.at(3).toInt(&ok);
            if (ok) {
                frames = qRound(total * framesPerSecond()) + extraFrames;
                frames = negative ? -frames : frames;
                if (allowNegative || frames >= 0)
                    return true;
            }
        } else if (parts.size() <= 3) {
            double total = 0.0;
            for (const auto &part : parts) {
                total = total * 60.0 + part.toDouble(&ok);
                if (!ok)
                    break;
            }
            if (ok) {
                seconds = negative ? -total : total;
                frames = qRound(seconds * framesPerSecond());
                if (allowNegative || frames >= 0)
                    return true;
            }
        }
        error = QStringLiteral("Invalid time \"%1\": use %2").arg(value.toString(), kTimeHelp);
        return false;
    } else {
        error = QStringLiteral("A time must be %1").arg(kTimeHelp);
        return false;
    }
    if (!std::isfinite(seconds) || (!allowNegative && seconds < 0.0)) {
        error = QStringLiteral("Invalid time %1").arg(seconds);
        return false;
    }
    frames = qRound(seconds * framesPerSecond());
    return true;
}

// ---------------------------------------------------------------------------------------
// Timeline access.

TimelineDock *timeline()
{
    return MAIN.timelineDock();
}

MultitrackModel *multitrack()
{
    return timeline()->model();
}

int trackCount()
{
    return multitrack()->trackList().size();
}

int videoTrackCount()
{
    int count = 0;
    for (const auto &track : multitrack()->trackList())
        if (track.type == VideoTrackType)
            ++count;
    return count;
}

/// The badge of a track as shown in the timeline: V2, V1, A1, A2...
QString trackCode(int trackIndex)
{
    const auto &tracks = multitrack()->trackList();
    const int videos = videoTrackCount();
    if (tracks.at(trackIndex).type == AudioTrackType)
        return QStringLiteral("A%1").arg(trackIndex - videos + 1);
    return QStringLiteral("V%1").arg(videos - trackIndex);
}

QStringList trackCodes()
{
    QStringList codes;
    for (int i = 0; i < trackCount(); ++i)
        codes << trackCode(i);
    return codes;
}

bool resolveTrack(const QJsonValue &value, int &trackIndex, QString &error)
{
    const int count = trackCount();
    if (value.isDouble()) {
        trackIndex = value.toInt(-1);
        if (trackIndex >= 0 && trackIndex < count && value.toDouble() == trackIndex)
            return true;
    } else if (value.isString()) {
        const auto code = value.toString().trimmed().toUpper();
        for (int i = 0; i < count; ++i) {
            if (trackCode(i) == code) {
                trackIndex = i;
                return true;
            }
        }
    }
    if (count == 0)
        error = QStringLiteral("The timeline has no tracks yet: use append_clip or add_track.");
    else
        error = QStringLiteral("Unknown track %1: use an index from 0 to %2 or one of %3.")
                    .arg(QString::fromUtf8(QJsonDocument(QJsonArray{value})
                                               .toJson(QJsonDocument::Compact)
                                               .mid(1)
                                               .chopped(1)))
                    .arg(count - 1)
                    .arg(trackCodes().join(", "));
    return false;
}

QModelIndex clipModelIndex(int trackIndex, int clipIndex)
{
    return multitrack()->index(clipIndex, 0, multitrack()->index(trackIndex));
}

int clipCountOf(int trackIndex)
{
    return multitrack()->rowCount(multitrack()->index(trackIndex));
}

bool isBlank(int trackIndex, int clipIndex)
{
    return clipModelIndex(trackIndex, clipIndex).data(MultitrackModel::IsBlankRole).toBool();
}

int realClipCount(int trackIndex)
{
    int count = 0;
    for (int i = 0; i < clipCountOf(trackIndex); ++i)
        if (!isBlank(trackIndex, i))
            ++count;
    return count;
}

/// The index of the clip (not a gap) that starts at \a frame, or -1.
int clipStartingAt(int trackIndex, int frame)
{
    for (int i = 0; i < clipCountOf(trackIndex); ++i) {
        const auto index = clipModelIndex(trackIndex, i);
        if (!index.data(MultitrackModel::IsBlankRole).toBool()
            && index.data(MultitrackModel::StartRole).toInt() == frame)
            return i;
    }
    return -1;
}

/// The clip of "uuid" or of "track" and "clip" in the arguments of a tool.
bool resolveClip(const QJsonObject &arguments, int &trackIndex, int &clipIndex, QString &error)
{
    if (!MAIN.isMultitrackValid()) {
        error = QStringLiteral("The timeline is empty: add a clip with append_clip first.");
        return false;
    }
    const auto uuidText = arguments.value("uuid").toString();
    if (!uuidText.isEmpty()) {
        const QUuid uuid(uuidText);
        if (uuid.isNull() || !multitrack()->findClipByUuid(uuid, trackIndex, clipIndex)) {
            error = QStringLiteral("No clip in the timeline has the uuid %1.").arg(uuidText);
            return false;
        }
        return true;
    }
    if (!arguments.contains("track") || !arguments.contains("clip")) {
        error = QStringLiteral("Pass the clip as \"track\" and \"clip\" (indices from "
                               "get_timeline) or as \"uuid\".");
        return false;
    }
    if (!resolveTrack(arguments.value("track"), trackIndex, error))
        return false;
    clipIndex = arguments.value("clip").toInt(-1);
    const int count = clipCountOf(trackIndex);
    if (clipIndex < 0 || clipIndex >= count) {
        error = QStringLiteral("Track %1 has %2 item(s): \"clip\" must be from 0 to %3.")
                    .arg(trackCode(trackIndex))
                    .arg(count)
                    .arg(count - 1);
        return false;
    }
    if (isBlank(trackIndex, clipIndex)) {
        error = QStringLiteral("Item %1 on %2 is a gap, not a clip.")
                    .arg(clipIndex)
                    .arg(trackCode(trackIndex));
        return false;
    }
    return true;
}

QString clipUuid(int trackIndex, int clipIndex)
{
    auto info = multitrack()->getClipInfo(trackIndex, clipIndex);
    if (!info)
        return QString();
    QUuid uuid;
    if (info->cut)
        uuid = MLT.uuid(*info->cut);
    if (uuid.isNull() && info->producer)
        uuid = MLT.uuid(*info->producer);
    return uuid.isNull() ? QString() : uuid.toString(QUuid::WithoutBraces);
}

// ---------------------------------------------------------------------------------------
// Media files: each path gets a short id (m1, m2...) that stays the same while Shotcut
// runs. Clips and playlist items refer to it, and every answer lists each path once in
// its "media" table, so a long path is not repeated for every clip that uses it.

QHash<QString, QString> &mediaIds()
{
    static QHash<QString, QString> ids;
    return ids;
}

/// The "media" table of the answer being built, filled by mediaRef().
QJsonObject *answerMedia = nullptr;

QString mediaRef(const QString &resource)
{
    auto &ids = mediaIds();
    auto id = ids.value(resource);
    if (id.isEmpty()) {
        id = QStringLiteral("m%1").arg(ids.size() + 1);
        ids.insert(resource, id);
    }
    if (answerMedia)
        answerMedia->insert(id, resource);
    return id;
}

/// The path of a media id, or an empty string.
QString mediaPath(const QString &id)
{
    return mediaIds().key(id.trimmed());
}

/// A name worth sending: the caption when it differs from the file name.
bool isOwnName(const QString &name, const QString &resource)
{
    return !name.isEmpty() && name != QFileInfo(resource).fileName();
}

QJsonObject clipJson(int trackIndex, int clipIndex, bool full = false)
{
    const auto index = clipModelIndex(trackIndex, clipIndex);
    const int start = index.data(MultitrackModel::StartRole).toInt();
    const int duration = index.data(MultitrackModel::DurationRole).toInt();
    QJsonObject clip{{"index", clipIndex},
                     {"start", secondsOf(start)},
                     {"end", secondsOf(start + duration)},
                     {"duration", secondsOf(duration)}};
    if (index.data(MultitrackModel::IsBlankRole).toBool()) {
        clip["blank"] = true;
        if (full)
            clip["frames"] = QJsonObject{{"start", start}, {"duration", duration}};
        return clip;
    }
    const int in = index.data(MultitrackModel::InPointRole).toInt();
    const int out = index.data(MultitrackModel::OutPointRole).toInt();
    const auto name = index.data(MultitrackModel::NameRole).toString();
    const auto resource = index.data(MultitrackModel::ResourceRole).toString();
    if (!resource.isEmpty())
        clip["media"] = mediaRef(resource);
    if (full || resource.isEmpty() || isOwnName(name, resource))
        clip["name"] = name;
    clip["in"] = secondsOf(in);
    clip["out"] = secondsOf(out);
    if (full)
        clip["frames"]
            = QJsonObject{{"start", start}, {"duration", duration}, {"in", in}, {"out", out}};
    if (index.data(MultitrackModel::IsTransitionRole).toBool())
        clip["transition"] = true;
    const int fadeIn = index.data(MultitrackModel::FadeInRole).toInt();
    if (fadeIn > 0)
        clip["fade_in"] = secondsOf(fadeIn);
    const int fadeOut = index.data(MultitrackModel::FadeOutRole).toInt();
    if (fadeOut > 0)
        clip["fade_out"] = secondsOf(fadeOut);
    if (index.data(MultitrackModel::IsFilteredRole).toBool())
        clip["filtered"] = true;
    const double speed = index.data(MultitrackModel::SpeedRole).toDouble();
    if (speed != 0.0 && speed != 1.0)
        clip["speed"] = speed;
    const int group = index.data(MultitrackModel::GroupRole).toInt();
    if (index.data(MultitrackModel::GroupRole).isValid() && group >= 0)
        clip["group"] = group;
    const auto uuid = clipUuid(trackIndex, clipIndex);
    if (!uuid.isEmpty())
        clip["uuid"] = uuid;
    return clip;
}

QJsonObject trackJson(int trackIndex, bool withClips, bool withBlanks, bool full = false)
{
    const auto index = multitrack()->index(trackIndex);
    const bool audio = index.data(MultitrackModel::IsAudioRole).toBool();
    QJsonObject track{{"index", trackIndex},
                      {"code", trackCode(trackIndex)},
                      {"name", index.data(MultitrackModel::NameRole).toString()},
                      {"type", audio ? "audio" : "video"},
                      {"muted", index.data(MultitrackModel::IsMuteRole).toBool()},
                      {"locked", index.data(MultitrackModel::IsLockedRole).toBool()},
                      {"duration", secondsOf(index.data(MultitrackModel::DurationRole).toInt())}};
    if (!audio)
        track["hidden"] = index.data(MultitrackModel::IsHiddenRole).toBool();
    if (withClips) {
        QJsonArray clips;
        for (int i = 0; i < clipCountOf(trackIndex); ++i) {
            if (withBlanks || !isBlank(trackIndex, i))
                clips.append(clipJson(trackIndex, i, full));
        }
        track["clips"] = clips;
    }
    return track;
}

/// The timeline; \a onlyTrack limits the tracks to one (-1: all).
QJsonObject timelineJson(bool withBlanks, bool full = false, int onlyTrack = -1)
{
    QJsonArray tracks;
    for (int i = 0; i < trackCount(); ++i) {
        if (onlyTrack < 0 || i == onlyTrack)
            tracks.append(trackJson(i, true, withBlanks, full));
    }
    int duration = 0;
    if (MAIN.multitrack() && MAIN.multitrack()->is_valid())
        duration = MAIN.multitrack()->get_length();
    QJsonArray selection;
    for (const auto &point : timeline()->selection())
        selection.append(QJsonObject{{"track", point.y()}, {"clip", point.x()}});
    return QJsonObject{{"tracks", tracks},
                       {"duration", timeJson(duration)},
                       {"fps", round3(framesPerSecond())},
                       {"current_track", timeline()->currentTrack()},
                       {"selection", selection},
                       {"playhead", timeJson(qMax(0, timeline()->position()))}};
}

/// Shows the project (timeline) in the viewer, like clicking its tab.
void showProjectInPlayer()
{
    if (MAIN.isMultitrackValid() && MAIN.player()->tabIndex() != Player::ProjectTabIndex)
        MAIN.player()->onTabBarClicked(Player::ProjectTabIndex);
}

// ---------------------------------------------------------------------------------------
// Playlist, sources and state.

PlaylistModel *playlistModel()
{
    return MAIN.playlistDock()->model();
}

int playlistCount()
{
    return MAIN.playlist() ? MAIN.playlist()->count() : 0;
}

QString mediaTypeName(int type)
{
    switch (type) {
    case PlaylistModel::Video:
        return QStringLiteral("video");
    case PlaylistModel::Image:
        return QStringLiteral("image");
    case PlaylistModel::Audio:
        return QStringLiteral("audio");
    default:
        return QStringLiteral("other");
    }
}

QJsonObject playlistItemJson(int row, bool full = false)
{
    QJsonObject item{{"index", row}};
    std::unique_ptr<Mlt::ClipInfo> info(MAIN.playlist()->clip_info(row));
    if (!info || !info->producer)
        return item;
    auto name = QString::fromUtf8(info->producer->get(kShotcutCaptionProperty));
    const auto resource = ProxyManager::resource(*info->producer);
    if (name.isEmpty())
        name = QFileInfo(resource).fileName();
    if (!resource.isEmpty())
        item["media"] = mediaRef(resource);
    if (full || resource.isEmpty() || isOwnName(name, resource))
        item["name"] = name;
    item["duration"] = secondsOf(info->frame_count);
    item["in"] = secondsOf(info->frame_in);
    item["out"] = secondsOf(info->frame_out);
    item["type"] = mediaTypeName(
        playlistModel()
            ->data(playlistModel()->index(row, 0), PlaylistModel::FIELD_MEDIA_TYPE_ENUM)
            .toInt());
    return item;
}

QJsonObject producerJson(Mlt::Producer *producer)
{
    if (!producer || !producer->is_valid())
        return QJsonObject();
    QJsonObject json{{"name", Util::producerTitle(*producer)},
                     {"duration", secondsOf(producer->get_playtime())},
                     {"service", QString::fromUtf8(producer->get("mlt_service"))}};
    const auto resource = ProxyManager::resource(*producer);
    if (!resource.isEmpty())
        json["media"] = mediaRef(resource);
    return json;
}

QJsonObject undoJson()
{
    auto stack = MAIN.undoStack();
    return QJsonObject{{"can_undo", stack->canUndo()},
                       {"undo", stack->undoText()},
                       {"can_redo", stack->canRedo()},
                       {"redo", stack->redoText()}};
}

QJsonObject playerJson()
{
    const bool project = MAIN.player()->tabIndex() == Player::ProjectTabIndex;
    int duration = 0;
    if (MLT.producer() && MLT.producer()->is_valid())
        duration = MLT.producer()->get_length();
    QJsonObject player{{"showing", project ? "project" : "source"},
                       {"playing", MLT.producer() && !MLT.isPaused()},
                       {"position", timeJson(MAIN.player()->position())},
                       {"duration", timeJson(duration)}};
    Mlt::Producer *source = project ? MLT.savedProducer() : MLT.producer();
    if (source && source->is_valid() && !MLT.isMultitrack() && !MLT.isPlaylist())
        player["source_clip"] = producerJson(source);
    else if (source && source->is_valid() && project)
        player["source_clip"] = producerJson(source);
    return player;
}

/// "16:9" for a common aspect ratio, else like "2.39:1".
QString aspectText(double ratio)
{
    static const int common[][2]
        = {{16, 9}, {9, 16}, {4, 3}, {3, 4}, {1, 1}, {4, 5}, {21, 9}, {2, 1}};
    for (const auto &pair : common) {
        if (qAbs(ratio - double(pair[0]) / pair[1]) < 0.01)
            return QStringLiteral("%1:%2").arg(pair[0]).arg(pair[1]);
    }
    return QStringLiteral("%1:1").arg(QString::number(ratio, 'f', 2));
}

QJsonObject profileJson()
{
    auto &profile = MLT.profile();
    const auto aspect = aspectText(profile.dar());
    // MLT keeps the description of the default profile while the automatic video mode
    // adapts the size and frame rate, so the description is built from the values.
    QJsonObject json{{"width", profile.width()},
                     {"height", profile.height()},
                     {"fps", round3(framesPerSecond())},
                     {"aspect", aspect},
                     {"progressive", profile.progressive() != 0},
                     {"description",
                      QStringLiteral("%1x%2, %3 fps, %4")
                          .arg(profile.width())
                          .arg(profile.height())
                          .arg(QString::number(framesPerSecond(), 'g', 4), aspect)}};
    const bool automatic = Settings.playerProfile().isEmpty();
    json["video_mode"] = automatic ? QStringLiteral("Automatic")
                                   : QString::fromUtf8(profile.description());
    // In the automatic mode the format follows the first clip added to an empty project.
    json["adapts_to_first_clip"] = automatic && !profile.is_explicit();
    return json;
}

QJsonObject stateJson()
{
    QJsonObject timelineInfo{{"tracks", trackCount()},
                             {"video_tracks", videoTrackCount()},
                             {"audio_tracks", trackCount() - videoTrackCount()}};
    if (MAIN.multitrack() && MAIN.multitrack()->is_valid())
        timelineInfo["duration"] = timeJson(MAIN.multitrack()->get_length());
    QJsonArray selection;
    for (const auto &point : timeline()->selection())
        selection.append(QJsonObject{{"track", point.y()}, {"clip", point.x()}});
    timelineInfo["selection"] = selection;
    timelineInfo["current_track"] = timeline()->currentTrack();
    return QJsonObject{{"application",
                        QJsonObject{{"name", QCoreApplication::applicationName()},
                                    {"version", QCoreApplication::applicationVersion()}}},
                       {"project",
                        QJsonObject{{"file", MAIN.fileName()},
                                    {"modified", MAIN.isWindowModified()}}},
                       {"profile", profileJson()},
                       {"player", playerJson()},
                       {"timeline", timelineInfo},
                       {"playlist", QJsonObject{{"items", playlistCount()}}},
                       {"undo", undoJson()}};
}

/// \a path, or the private copy that an app from the Microsoft Store (such as Claude
/// Desktop) keeps of the files it writes under AppData.
QString localPath(const QString &path)
{
#ifdef Q_OS_WIN
    return QDir::fromNativeSeparators(Mcp::unvirtualizedPath(path,
                                                             qEnvironmentVariable("APPDATA"),
                                                             qEnvironmentVariable("LOCALAPPDATA")));
#else
    return path;
#endif
}

/// The error for a file that does not exist, with the usual cause on Windows.
QString fileNotFound(const QString &path)
{
    auto message = QStringLiteral("File not found: %1").arg(path);
    if (path.contains(QLatin1String("/AppData/"), Qt::CaseInsensitive)
        || path.contains(QLatin1String("\\AppData\\"), Qt::CaseInsensitive)) {
        message += QStringLiteral(
            ". Apps from the Microsoft Store (such as Claude Desktop) keep the files they write "
            "in AppData in a private folder that other programs cannot see: save the file in "
            "Documents, Videos or Desktop instead.");
    }
    return message;
}

/// The MLT XML of a clip from the playlist ("playlist_index"), a file ("path") or a media
/// id from get_timeline or get_playlist ("media").
bool sourceXml(QJsonObject arguments, QString &xml, QString &error)
{
    if (!arguments.value("media").toString().isEmpty()) {
        const auto path = mediaPath(arguments.value("media").toString());
        if (path.isEmpty()) {
            error = QStringLiteral("Unknown media id \"%1\": use an id from the \"media\" table of "
                                   "get_timeline or get_playlist.")
                        .arg(arguments.value("media").toString());
            return false;
        }
        if (!arguments.value("path").toString().isEmpty()
            || !arguments.value("playlist_index").isUndefined()) {
            error = QStringLiteral("Pass only one of \"playlist_index\", \"path\" and \"media\".");
            return false;
        }
        arguments.insert("path", path);
    }
    const bool hasIndex = arguments.contains("playlist_index")
                          && !arguments.value("playlist_index").isNull();
    const bool hasPath = !arguments.value("path").toString().isEmpty();
    if (hasIndex == hasPath) {
        error = QStringLiteral("Pass one of \"playlist_index\" (from get_playlist), \"path\" (a "
                               "media file) or \"media\" (an id such as \"m1\").");
        return false;
    }
    if (hasIndex) {
        const int row = arguments.value("playlist_index").toInt(-1);
        if (row < 0 || row >= playlistCount()) {
            error = QStringLiteral("The playlist has %1 item(s): \"playlist_index\" must be from "
                                   "0 to %2.")
                        .arg(playlistCount())
                        .arg(playlistCount() - 1);
            return false;
        }
        std::unique_ptr<Mlt::ClipInfo> info(MAIN.playlist()->clip_info(row));
        if (!info || !info->producer || !info->producer->is_valid()) {
            error = QStringLiteral("Playlist item %1 cannot be used.").arg(row);
            return false;
        }
        // Like opening the item from the playlist.
        Mlt::Producer producer(info->producer);
        producer.set_in_and_out(info->frame_in, info->frame_out);
        xml = MLT.XML(&producer);
        return true;
    }
    const auto path = localPath(QDir::fromNativeSeparators(arguments.value("path").toString()));
    const QFileInfo file(path);
    if (!file.isFile()) {
        error = fileNotFound(path);
        return false;
    }
    if (MLT.checkFile(file.absoluteFilePath())) {
        error = QStringLiteral("Shotcut cannot open %1.").arg(path);
        return false;
    }
    Mlt::Producer raw(MLT.profile(), file.absoluteFilePath().toUtf8().constData());
    if (!raw.is_valid()) {
        error = QStringLiteral("Shotcut cannot open %1.").arg(path);
        return false;
    }
    // Configured like files added to the playlist (image duration, chains...).
    std::unique_ptr<Mlt::Producer> producer(MLT.setupNewProducer(&raw));
    producer->set(kShotcutSkipConvertProperty, 1);
    xml = MLT.XML(producer.get());
    return true;
}

// ---------------------------------------------------------------------------------------
// Filters of timeline clips.

FilterController *filters()
{
    return MAIN.filterController();
}

/// Selects the clip so that its filters are loaded in the filter controller.
bool loadClipFilters(int trackIndex, int clipIndex, QString &error)
{
    showProjectInPlayer();
    timeline()->setSelection(QList<QPoint>() << QPoint(clipIndex, trackIndex));
    timeline()->flushSelection();
    auto info = multitrack()->getClipInfo(trackIndex, clipIndex);
    auto model = filters()->attachedModel();
    if (!info || !info->producer || !model->producer()
        || model->producer()->get_producer() != info->producer->get_producer()) {
        error = QStringLiteral("Could not load the filters of clip %1 on %2.")
                    .arg(clipIndex)
                    .arg(trackCode(trackIndex));
        return false;
    }
    return true;
}

bool isInternalProperty(const QString &name)
{
    static const QSet<QString> internal{"in", "out", "disable", "length", "eof", "kdenlive_id"};
    return name.startsWith(QLatin1Char('_')) || name.startsWith(QLatin1String("shotcut:"))
           || name.startsWith(QLatin1String("mlt_")) || internal.contains(name);
}

QJsonObject filterJson(int row)
{
    auto model = filters()->attachedModel();
    QJsonObject filter{{"index", row}, {"name", model->name(row)}};
    if (auto meta = model->getMetadata(row))
        filter["id"] = meta->uniqueId();
    filter["enabled"] = model->data(model->index(row), Qt::CheckStateRole).toInt() == Qt::Checked;
    std::unique_ptr<Mlt::Service> service(model->getService(row));
    if (service && service->is_valid()) {
        QJsonObject parameters;
        for (int i = 0; i < service->count(); ++i) {
            const auto name = QString::fromUtf8(service->get_name(i));
            const char *value = service->get(i);
            if (name.isEmpty() || !value || isInternalProperty(name))
                continue;
            parameters[name] = QString::fromUtf8(value);
        }
        filter["parameters"] = parameters;
    }
    return filter;
}

QJsonArray clipFiltersJson()
{
    QJsonArray list;
    for (int row = 0; row < filters()->attachedModel()->rowCount(); ++row)
        list.append(filterJson(row));
    return list;
}

bool setFilterParameters(QmlFilter *filter, const QJsonObject &parameters, QString &error)
{
    for (auto it = parameters.constBegin(); it != parameters.constEnd(); ++it) {
        const auto &value = it.value();
        if (value.isBool()) {
            filter->set(it.key(), value.toBool());
        } else if (value.isDouble()) {
            const double number = value.toDouble();
            if (std::floor(number) == number && std::fabs(number) < 2147483647.0)
                filter->set(it.key(), int(number));
            else
                filter->set(it.key(), number);
        } else if (value.isString()) {
            filter->set(it.key(), value.toString());
        } else {
            error = QStringLiteral("The value of \"%1\" must be a string, a number or a boolean.")
                        .arg(it.key());
            return false;
        }
    }
    return true;
}

bool resolveFilterRow(const QJsonObject &arguments, int &row, QString &error)
{
    row = arguments.value("filter_index").toInt(-1);
    const int count = filters()->attachedModel()->rowCount();
    if (row < 0 || row >= count) {
        error = count ? QStringLiteral("The clip has %1 filter(s): \"filter_index\" must be "
                                       "from 0 to %2 (see get_clip_filters).")
                            .arg(count)
                            .arg(count - 1)
                      : QStringLiteral("The clip has no filters.");
        return false;
    }
    return true;
}

// ---------------------------------------------------------------------------------------
// Actions.

QString actionLabel(QAction *action)
{
    auto label = action->property(ShotcutActions::displayProperty).toString();
    if (label.isEmpty())
        label = action->iconText();
    return label.remove(QLatin1Char('&'));
}

/// Actions that quit or restart Shotcut would cut the connection of the agent.
bool isBlockedAction(const QString &name, QAction *action)
{
    static const QSet<QString> blocked{"actionExit",
                                       "actionReset",
                                       "actionAppDataSet",
                                       "actionUpgrade",
                                       "actionSystemTheme",
                                       "actionSystemFusion",
                                       "actionFusionDark",
                                       "actionClassicFusionDark",
                                       "actionFusionLight"};
    return blocked.contains(name)
           || actionLabel(action).startsWith(QLatin1String("Settings > Language"));
}

QJsonObject actionJson(const QString &name, QAction *action)
{
    QJsonObject object{{"name", name},
                       {"label", actionLabel(action)},
                       {"enabled", action->isEnabled()}};
    if (action->isCheckable()) {
        object["checkable"] = true;
        object["checked"] = action->isChecked();
    }
    const auto shortcut = action->shortcut().toString(QKeySequence::PortableText);
    if (!shortcut.isEmpty())
        object["shortcut"] = shortcut;
    return object;
}

// ---------------------------------------------------------------------------------------
// Tool definitions.

QJsonObject schema(const char *json)
{
    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(QByteArray(json), &error);
    if (error.error != QJsonParseError::NoError)
        LOG_ERROR() << "Invalid tool schema:" << error.errorString() << json;
    return document.object();
}

QJsonObject readOnly()
{
    return QJsonObject{{"readOnlyHint", true}, {"openWorldHint", false}};
}

QJsonObject editing(bool idempotent = false, bool destructive = false)
{
    return QJsonObject{{"readOnlyHint", false},
                       {"destructiveHint", destructive},
                       {"idempotentHint", idempotent},
                       {"openWorldHint", false}};
}

Mcp::ToolResult failure(const QString &message)
{
    return Mcp::ToolResult::failure(message);
}

} // namespace

AiTools::AiTools(QObject *parent)
    : QObject(parent)
{}

Mcp::ToolResult AiTools::run(const std::function<Mcp::ToolResult()> &body)
{
    if (m_busy)
        return failure(QStringLiteral(
            "Shotcut AI is busy with another request, probably waiting for a dialog in the "
            "application. Try again after the user closes it."));
    QScopedValueRollback<bool> busy(m_busy, true);
    QJsonObject media;
    QScopedValueRollback<QJsonObject *> table(answerMedia, &media);
    auto result = body();
    if (!result.isError && !media.isEmpty())
        result.data.insert("media", media);
    return result;
}

Mcp::ToolResult AiTools::edit(const QString &title, const std::function<Mcp::ToolResult()> &body)
{
    return run([&]() {
        auto stack = MAIN.undoStack();
        const auto text = tr("AI: %1").arg(title);
        stack->beginMacro(text);
        auto result = body();
        stack->endMacro();
        // Drop the step when nothing changed.
        const int index = stack->index();
        if (index > 0) {
            auto command = const_cast<QUndoCommand *>(stack->command(index - 1));
            if (command && command->text() == text && command->childCount() == 0) {
                command->setObsolete(true);
                stack->undo();
            }
        }
        if (!result.isError)
            MAIN.showStatusMessage(text, 3);
        return result;
    });
}

void AiTools::registerTools(Mcp::Server &server)
{
    auto add = [&server](const char *name,
                         const QString &title,
                         const QString &description,
                         const char *inputSchema,
                         const QJsonObject &annotations,
                         std::function<Mcp::ToolResult(const QJsonObject &)> handler) {
        Mcp::Tool tool;
        tool.name = QString::fromLatin1(name);
        tool.title = title;
        tool.description = description;
        tool.inputSchema = schema(inputSchema);
        tool.annotations = annotations;
        tool.handler = std::move(handler);
        server.addTool(tool);
    };

    // --- State -------------------------------------------------------------------------

    add("get_state",
        "Get state",
        "The state of Shotcut AI: project file and whether it has unsaved changes, video "
        "profile (size, fps), player (project or source clip, playing, position, duration), "
        "timeline summary and selection, playlist size and what undo/redo would do. Call it "
        "first.",
        R"json({"type": "object", "properties": {}, "additionalProperties": false})json",
        readOnly(),
        [this](const QJsonObject &) {
            return run([]() { return Mcp::ToolResult::success(stateJson()); });
        });

    add("get_timeline",
        "Get timeline",
        "The tracks of the timeline from top to bottom (index, code such as V1 or A1, name, "
        "type, muted, hidden, locked) with their clips (index within the track, start, end, "
        "duration, in and out points in seconds, media id, fades, whether it has filters, "
        "uuid), the playhead and the selection. Each clip refers to its file by a media id "
        "(m1, m2...); the \"media\" table of the answer gives the path of each id once. A "
        "clip has a name only when it differs from its file name. Gaps are left out unless "
        "include_gaps is true, so clip indices can skip numbers.",
        R"json({"type": "object",
                "properties": {
                  "include_gaps": {"type": "boolean",
                    "description": "Also list the gaps (blank items) between clips."},
                  "track": {"type": ["integer", "string"],
                    "description": "Only this track (index or code such as V1)."},
                  "detail": {"type": "string", "enum": ["compact", "full"],
                    "description": "full adds frame numbers and every clip name (default compact)."}},
                "additionalProperties": false})json",
        readOnly(),
        [this](const QJsonObject &arguments) {
            return run([&]() {
                int track = -1;
                if (arguments.contains("track")) {
                    QString error;
                    if (!resolveTrack(arguments.value("track"), track, error))
                        return failure(error);
                }
                return Mcp::ToolResult::success(
                    timelineJson(arguments.value("include_gaps").toBool(),
                                 arguments.value("detail").toString() == QLatin1String("full"),
                                 track));
            });
        });

    add("get_playlist",
        "Get playlist",
        "The media in the playlist (the Media panel): index, media id, type (video, image, "
        "audio, other), duration and in/out points in seconds; the \"media\" table of the "
        "answer gives the path of each id. Use the index as playlist_index, or the id as "
        "media, in append_clip, insert_clip or overwrite_clip.",
        R"json({"type": "object",
                "properties": {
                  "detail": {"type": "string", "enum": ["compact", "full"],
                    "description": "full adds every item name (default compact)."}},
                "additionalProperties": false})json",
        readOnly(),
        [this](const QJsonObject &arguments) {
            return run([&]() {
                const bool full = arguments.value("detail").toString() == QLatin1String("full");
                QJsonArray items;
                for (int row = 0; row < playlistCount(); ++row)
                    items.append(playlistItemJson(row, full));
                return Mcp::ToolResult::success(QJsonObject{{"items", items}});
            });
        });

    add("get_frame",
        "Get video frame",
        "Returns an image of the video: without position, the frame that the viewer shows "
        "now; with position, the frame at that time of what the viewer plays (the project "
        "or the source clip), without moving the playhead. Use it to check the result of an "
        "edit.",
        R"json({"type": "object",
                "properties": {
                  "position": {"type": ["number", "string"],
                    "description": "Seconds or timecode; default: the frame shown now."},
                  "width": {"type": "integer", "minimum": 64, "maximum": 1920,
                    "description": "Image width in pixels (default 640)."}},
                "additionalProperties": false})json",
        readOnly(),
        [this](const QJsonObject &arguments) {
            return run([&]() {
                if (!MLT.producer() || !MLT.producer()->is_valid())
                    return failure(QStringLiteral("Nothing is open in the viewer."));
                const int width = arguments.value("width").toInt(640);
                QImage image;
                int position = MAIN.player()->position();
                QString origin = QStringLiteral("viewer");
                const bool atPosition = arguments.contains("position")
                                        && !arguments.value("position").isNull();
                if (atPosition) {
                    QString error;
                    if (!parseTime(arguments.value("position"), position, error))
                        return failure(error);
                } else if (auto videoWidget = qobject_cast<Mlt::VideoWidget *>(MLT.videoWidget())) {
                    image = videoWidget->image();
                }
                if (image.isNull()) {
                    // Render a copy, so that the player and the playhead do not move.
                    Mlt::Producer copy(MLT.profile(),
                                       "xml-string",
                                       MLT.XML(MLT.producer()).toUtf8().constData());
                    if (!copy.is_valid())
                        return failure(QStringLiteral("Could not render the video."));
                    position = qBound(0, position, qMax(0, copy.get_length() - 1));
                    const double aspect = MLT.profile().dar() > 0.0 ? MLT.profile().dar()
                                                                    : 16.0 / 9.0;
                    image = MLT.image(copy, position, width, qRound(width / aspect / 2.0) * 2);
                    origin = QStringLiteral("render");
                }
                if (image.isNull())
                    return failure(QStringLiteral("Could not get a frame."));
                if (image.width() > width)
                    image = image.scaledToWidth(width, Qt::SmoothTransformation);
                QByteArray bytes;
                QBuffer buffer(&bytes);
                buffer.open(QIODevice::WriteOnly);
                QString mimeType = QStringLiteral("image/jpeg");
                if (!image.convertToFormat(QImage::Format_RGB888).save(&buffer, "JPG", 85)) {
                    bytes.clear();
                    buffer.seek(0);
                    image.save(&buffer, "PNG");
                    mimeType = QStringLiteral("image/png");
                }
                auto result = Mcp::ToolResult::success(QJsonObject{{"position", timeJson(position)},
                                                                   {"width", image.width()},
                                                                   {"height", image.height()},
                                                                   {"from", origin}});
                result.extraContent.append(
                    QJsonObject{{"type", "image"},
                                {"data", QString::fromLatin1(bytes.toBase64())},
                                {"mimeType", mimeType}});
                return result;
            });
        });

    add("list_actions",
        "List actions",
        "The named actions of Shotcut (menus, toolbars and shortcuts) that run_action can "
        "trigger: name, label such as \"Timeline > Split At Playhead\", enabled, checked "
        "state and shortcut. Filter them with query, for example \"split\", \"marker\" or "
        "\"zoom\".",
        R"json({"type": "object",
                "properties": {"query": {"type": "string",
                    "description": "Case-insensitive text to find in the name or label."}},
                "additionalProperties": false})json",
        readOnly(),
        [this](const QJsonObject &arguments) {
            return run([&]() {
                const auto query = arguments.value("query").toString().trimmed();
                auto names = Actions.keys();
                std::sort(names.begin(), names.end());
                QJsonArray list;
                for (const auto &name : names) {
                    QAction *action = Actions[name];
                    if (!action || isBlockedAction(name, action))
                        continue;
                    if (!query.isEmpty() && !name.contains(query, Qt::CaseInsensitive)
                        && !actionLabel(action).contains(query, Qt::CaseInsensitive))
                        continue;
                    list.append(actionJson(name, action));
                }
                return Mcp::ToolResult::success(
                    QJsonObject{{"actions", list}, {"count", list.size()}});
            });
        });

    add("list_filters",
        "List filters",
        "The video and audio filters that add_filter can attach: id, name and type. Filter "
        "them with query (for example \"blur\", \"brightness\", \"text\" or \"volume\") and "
        "type.",
        R"json({"type": "object",
                "properties": {
                  "query": {"type": "string",
                    "description": "Case-insensitive text to find in the name, id or keywords."},
                  "type": {"type": "string", "enum": ["video", "audio"]}},
                "additionalProperties": false})json",
        readOnly(),
        [this](const QJsonObject &arguments) {
            return run([&]() {
                const auto query = arguments.value("query").toString().trimmed();
                const auto type = arguments.value("type").toString();
                auto model = filters()->metadataModel();
                QJsonArray list;
                for (int i = 0; i < model->sourceRowCount(); ++i) {
                    QmlMetadata *meta = model->getFromSource(i);
                    if (!meta || meta->isHidden() || meta->isDeprecated())
                        continue;
                    if (meta->type() != QmlMetadata::Filter && meta->type() != QmlMetadata::Link
                        && meta->type() != QmlMetadata::FilterSet)
                        continue;
                    if (meta->needsGPU() && !Settings.playerGPU())
                        continue;
                    const auto kind = meta->isAudio() ? QStringLiteral("audio")
                                                      : QStringLiteral("video");
                    if (!type.isEmpty() && type != kind)
                        continue;
                    const auto keywords = meta->property("keywords").toString();
                    if (!query.isEmpty() && !meta->name().contains(query, Qt::CaseInsensitive)
                        && !meta->uniqueId().contains(query, Qt::CaseInsensitive)
                        && !keywords.contains(query, Qt::CaseInsensitive))
                        continue;
                    QJsonObject filter{{"id", meta->uniqueId()},
                                       {"name", meta->name()},
                                       {"type", kind}};
                    if (meta->type() == QmlMetadata::Link)
                        filter["time_effect"] = true;
                    list.append(filter);
                }
                return Mcp::ToolResult::success(
                    QJsonObject{{"filters", list}, {"count", list.size()}});
            });
        });

    add("get_clip_filters",
        "Get clip filters",
        "The filters of a timeline clip in order: index, id, name, enabled and parameters "
        "(MLT properties). Selects the clip, like clicking it.",
        R"json({"type": "object",
                "properties": {
                  "track": {"type": ["integer", "string"], "description": "Track index or code (V1, A1...)."},
                  "clip": {"type": "integer", "minimum": 0, "description": "Clip index in the track."},
                  "uuid": {"type": "string", "description": "Alternative to track and clip."}},
                "additionalProperties": false})json",
        readOnly(),
        [this](const QJsonObject &arguments) {
            return run([&]() {
                int track = -1, clip = -1;
                QString error;
                if (!resolveClip(arguments, track, clip, error)
                    || !loadClipFilters(track, clip, error))
                    return failure(error);
                return Mcp::ToolResult::success(QJsonObject{{"track", track},
                                                            {"clip", clipJson(track, clip)},
                                                            {"filters", clipFiltersJson()}});
            });
        });

    // --- Player ------------------------------------------------------------------------

    add("play",
        "Play",
        "Plays what the viewer shows (the project or the source clip). speed can be "
        "negative to play backward.",
        R"json({"type": "object",
                "properties": {"speed": {"type": "number", "minimum": -32, "maximum": 32,
                    "description": "1 is normal speed (default)."}},
                "additionalProperties": false})json",
        editing(true),
        [this](const QJsonObject &arguments) {
            return run([&]() {
                if (!MLT.producer() || !MLT.producer()->is_valid())
                    return failure(QStringLiteral("Nothing is open in the viewer."));
                const double speed = arguments.value("speed").toDouble(1.0);
                if (speed == 0.0)
                    return failure(QStringLiteral("speed cannot be 0: use pause."));
                MAIN.player()->play(speed);
                return Mcp::ToolResult::success(playerJson());
            });
        });

    add("pause",
        "Pause",
        "Pauses the player.",
        R"json({"type": "object", "properties": {}, "additionalProperties": false})json",
        editing(true),
        [this](const QJsonObject &) {
            return run([]() {
                MAIN.player()->pause();
                return Mcp::ToolResult::success(playerJson());
            });
        });

    add("seek",
        "Seek",
        "Moves the playhead of the viewer to a time. target chooses the project (timeline) "
        "or the source clip; by default, what the viewer shows.",
        R"json({"type": "object",
                "properties": {
                  "position": {"type": ["number", "string"], "description": "Seconds or timecode."},
                  "target": {"type": "string", "enum": ["project", "source"]}},
                "required": ["position"], "additionalProperties": false})json",
        editing(true),
        [this](const QJsonObject &arguments) {
            return run([&]() {
                int frames = 0;
                QString error;
                if (!parseTime(arguments.value("position"), frames, error))
                    return failure(error);
                const auto target = arguments.value("target").toString();
                if (target == QLatin1String("project")) {
                    if (!MAIN.isMultitrackValid())
                        return failure(QStringLiteral("The timeline is empty."));
                    showProjectInPlayer();
                } else if (target == QLatin1String("source")) {
                    if (MAIN.player()->tabIndex() != Player::SourceTabIndex) {
                        if (!MLT.savedProducer() || !MLT.savedProducer()->is_valid())
                            return failure(QStringLiteral("There is no source clip."));
                        MAIN.player()->onTabBarClicked(Player::SourceTabIndex);
                    }
                }
                if (!MLT.producer() || !MLT.producer()->is_valid())
                    return failure(QStringLiteral("Nothing is open in the viewer."));
                frames = qBound(0, frames, qMax(0, MLT.producer()->get_length() - 1));
                MAIN.player()->seek(frames);
                // The player reports the new position once the frame is shown.
                auto player = playerJson();
                player["position"] = timeJson(frames);
                return Mcp::ToolResult::success(player);
            });
        });

    add("step",
        "Step frames",
        "Moves the playhead by a number of frames (negative goes back).",
        R"json({"type": "object",
                "properties": {"frames": {"type": "integer"}},
                "required": ["frames"], "additionalProperties": false})json",
        editing(),
        [this](const QJsonObject &arguments) {
            return run([&]() {
                if (!MLT.producer() || !MLT.producer()->is_valid())
                    return failure(QStringLiteral("Nothing is open in the viewer."));
                const int target = qBound(0,
                                          MAIN.player()->position()
                                              + arguments.value("frames").toInt(),
                                          qMax(0, MLT.producer()->get_length() - 1));
                MAIN.player()->seek(target);
                auto player = playerJson();
                player["position"] = timeJson(target);
                return Mcp::ToolResult::success(player);
            });
        });

    // --- Undo and actions --------------------------------------------------------------

    add("undo",
        "Undo",
        "Undoes the last change (of the user or of an AI tool), like Ctrl+Z.",
        R"json({"type": "object", "properties": {}, "additionalProperties": false})json",
        editing(),
        [this](const QJsonObject &) {
            return run([]() {
                auto stack = MAIN.undoStack();
                if (!stack->canUndo())
                    return failure(QStringLiteral("There is nothing to undo."));
                const auto text = stack->undoText();
                stack->undo();
                MAIN.showStatusMessage(tr("AI: Undo %1").arg(text), 3);
                return Mcp::ToolResult::success(QJsonObject{{"undone", text}, {"undo", undoJson()}});
            });
        });

    add("redo",
        "Redo",
        "Redoes the last undone change, like Ctrl+Shift+Z.",
        R"json({"type": "object", "properties": {}, "additionalProperties": false})json",
        editing(),
        [this](const QJsonObject &) {
            return run([]() {
                auto stack = MAIN.undoStack();
                if (!stack->canRedo())
                    return failure(QStringLiteral("There is nothing to redo."));
                const auto text = stack->redoText();
                stack->redo();
                MAIN.showStatusMessage(tr("AI: Redo %1").arg(text), 3);
                return Mcp::ToolResult::success(QJsonObject{{"redone", text}, {"undo", undoJson()}});
            });
        });

    add("run_action",
        "Run action",
        "Triggers a named Shotcut action from list_actions, like its menu item or shortcut "
        "(for example timelineSplitAction, timelineZoomFitAction or playerSetInAction). For "
        "a checkable action, pass checked to set its state. Actions that open a dialog wait "
        "until the user closes it; actions that quit or restart Shotcut are not available.",
        R"json({"type": "object",
                "properties": {
                  "name": {"type": "string"},
                  "checked": {"type": "boolean"}},
                "required": ["name"], "additionalProperties": false})json",
        editing(),
        [this](const QJsonObject &arguments) {
            const auto name = arguments.value("name").toString();
            QAction *action = Actions[name];
            const auto title = action ? actionLabel(action).section(QLatin1String(" > "), -1)
                                      : name;
            return edit(title, [&]() {
                if (!action) {
                    QStringList similar;
                    for (const auto &key : Actions.keys()) {
                        QAction *candidate = Actions[key];
                        if (key.contains(name, Qt::CaseInsensitive)
                            || (candidate
                                && actionLabel(candidate).contains(name, Qt::CaseInsensitive)))
                            similar << key;
                    }
                    std::sort(similar.begin(), similar.end());
                    similar = similar.mid(0, 10);
                    return failure(
                        QStringLiteral("Unknown action \"%1\".%2 Use list_actions to "
                                       "find the name.")
                            .arg(name,
                                 similar.isEmpty()
                                     ? QString()
                                     : QStringLiteral(" Similar: %1.").arg(similar.join(", "))));
                }
                if (isBlockedAction(name, action))
                    return failure(QStringLiteral("%1 quits or restarts Shotcut, so AI agents "
                                                  "cannot run it.")
                                       .arg(name));
                if (!action->isEnabled())
                    return failure(
                        QStringLiteral("%1 is disabled right now.").arg(actionLabel(action)));
                if (arguments.contains("checked") && !arguments.value("checked").isNull()) {
                    if (!action->isCheckable())
                        return failure(QStringLiteral("%1 is not checkable.").arg(name));
                    if (action->isChecked() != arguments.value("checked").toBool())
                        action->trigger();
                } else {
                    action->trigger();
                }
                return Mcp::ToolResult::success(actionJson(name, action));
            });
        });

    // --- Project and media -------------------------------------------------------------

    add("open_media",
        "Open media",
        "Opens a media file in the Source viewer (not in the project), to look at it or "
        "use it with other tools. Use open_project for .mlt projects.",
        R"json({"type": "object",
                "properties": {"path": {"type": "string", "description": "Absolute path of a video, audio or image file."}},
                "required": ["path"], "additionalProperties": false})json",
        editing(),
        [this](const QJsonObject &arguments) {
            return run([&]() {
                const auto path = localPath(
                    QDir::fromNativeSeparators(arguments.value("path").toString()));
                const QFileInfo file(path);
                if (!file.isFile())
                    return failure(fileNotFound(path));
                if (file.suffix().toLower() == QLatin1String("mlt"))
                    return failure(
                        QStringLiteral(
                            "%1 is a project: use open_project, or add_to_playlist to use it as a "
                            "clip.")
                            .arg(path));
                Mlt::Properties properties;
                properties.set(kShotcutSkipConvertProperty, 1);
                MAIN.open(file.absoluteFilePath(), &properties, false, true);
                if (!MLT.producer() || !MLT.producer()->is_valid() || !MLT.isClip())
                    return failure(QStringLiteral("Shotcut could not open %1.").arg(path));
                return Mcp::ToolResult::success(
                    QJsonObject{{"source_clip", producerJson(MLT.producer())},
                                {"player", playerJson()}});
            });
        });

    add("add_to_playlist",
        "Add to playlist",
        "Adds media files (or folders of media) to the end of the playlist, like dropping "
        "them on the Media panel. Returns the new playlist items.",
        R"json({"type": "object",
                "properties": {"paths": {"type": "array", "minItems": 1,
                    "items": {"type": "string"}, "description": "Absolute paths."}},
                "required": ["paths"], "additionalProperties": false})json",
        editing(),
        [this](const QJsonObject &arguments) {
            return edit(tr("Add to playlist"), [&]() {
                QStringList paths;
                for (const auto &value : arguments.value("paths").toArray()) {
                    const auto path = localPath(QDir::fromNativeSeparators(value.toString()));
                    if (!QFileInfo::exists(path))
                        return failure(fileNotFound(path));
                    paths << QFileInfo(path).absoluteFilePath();
                }
                const int before = playlistCount();
                MAIN.playlistDock()->appendFiles(paths);
                QJsonArray added;
                for (int row = before; row < playlistCount(); ++row)
                    added.append(playlistItemJson(row));
                if (added.isEmpty())
                    return failure(QStringLiteral("Shotcut could not add the files."));
                return Mcp::ToolResult::success(
                    QJsonObject{{"added", added}, {"playlist_items", playlistCount()}});
            });
        });

    add("open_project",
        "Open project",
        "Opens a Shotcut project (.mlt), replacing the current one. If the current project has "
        "unsaved changes, it fails unless discard_changes is true (save_project first to keep "
        "them).",
        R"json({"type": "object",
                "properties": {
                  "path": {"type": "string", "description": "Absolute path of the .mlt file."},
                  "discard_changes": {"type": "boolean"}},
                "required": ["path"], "additionalProperties": false})json",
        editing(false, true),
        [this](const QJsonObject &arguments) {
            return run([&]() {
                const auto path = localPath(
                    QDir::fromNativeSeparators(arguments.value("path").toString()));
                const QFileInfo file(path);
                if (!file.isFile())
                    return failure(fileNotFound(path));
                if (file.suffix().toLower() != QLatin1String("mlt"))
                    return failure(QStringLiteral("A project is a .mlt file."));
                if (MAIN.isWindowModified()) {
                    if (!arguments.value("discard_changes").toBool())
                        return failure(QStringLiteral(
                            "The current project has unsaved changes. Call save_project first, or "
                            "open_project with discard_changes: true to lose them."));
                    MAIN.setWindowModified(false);
                }
                MAIN.open(file.absoluteFilePath());
                if (QFileInfo(MAIN.fileName()).absoluteFilePath() != file.absoluteFilePath())
                    return failure(QStringLiteral("Shotcut could not open %1.").arg(path));
                return Mcp::ToolResult::success(stateJson());
            });
        });

    add("save_project",
        "Save project",
        "Saves the project. Without path it saves to the current file; with path (a .mlt "
        "file) it saves there and continues with that file, like Save As. An existing file "
        "other than the current one is only replaced with overwrite: true.",
        R"json({"type": "object",
                "properties": {
                  "path": {"type": "string", "description": "Absolute path; .mlt is added if missing."},
                  "overwrite": {"type": "boolean"}},
                "additionalProperties": false})json",
        editing(false, true),
        [this](const QJsonObject &arguments) {
            return run([&]() {
                auto path = QDir::fromNativeSeparators(arguments.value("path").toString().trimmed());
                const auto current = MAIN.fileName();
                if (path.isEmpty()) {
                    if (current.isEmpty())
                        return failure(QStringLiteral(
                            "The project has no file yet: pass a path ending in .mlt."));
                    path = current;
                }
                if (!path.endsWith(QLatin1String(".mlt"), Qt::CaseInsensitive))
                    path += QLatin1String(".mlt");
                const QFileInfo file(path);
                if (file.isRelative())
                    return failure(QStringLiteral("Use an absolute path."));
                const bool isCurrent = !current.isEmpty()
                                       && QFileInfo(current).absoluteFilePath()
                                              == file.absoluteFilePath();
                if (file.exists() && !isCurrent && !arguments.value("overwrite").toBool())
                    return failure(QStringLiteral("%1 exists: pass overwrite: true to replace it.")
                                       .arg(file.absoluteFilePath()));
                const QFileInfo folder(file.absolutePath());
                if (!folder.isDir() || !folder.isWritable() || (file.exists() && !file.isWritable()))
                    return failure(QStringLiteral("Cannot write %1.").arg(file.absoluteFilePath()));
                if (isCurrent)
                    MAIN.on_actionSave_triggered();
                else
                    MAIN.newProject(file.absoluteFilePath());
                if (!QFileInfo::exists(file.absoluteFilePath()) || MAIN.isWindowModified())
                    return failure(QStringLiteral("Saving %1 failed.").arg(file.absoluteFilePath()));
                return Mcp::ToolResult::success(
                    QJsonObject{{"file", MAIN.fileName()}, {"modified", MAIN.isWindowModified()}});
            });
        });

    // --- Timeline editing --------------------------------------------------------------

    add("append_clip",
        "Append clip",
        "Adds a clip at the end of a track, from the playlist (playlist_index), a file (path) "
        "or a media id (media). An empty timeline gets its first tracks. Returns the new clip.",
        R"json({"type": "object",
                "properties": {
                  "track": {"type": ["integer", "string"],
                    "description": "Track index or code (V1, A1...); default: the current track."},
                  "playlist_index": {"type": "integer", "minimum": 0,
                    "description": "A playlist item (get_playlist)."},
                  "path": {"type": "string", "description": "Or a media file (absolute path)."},
                  "media": {"type": "string",
                    "description": "Or a media id (m1...) from get_timeline or get_playlist."}},
                "additionalProperties": false})json",
        editing(),
        [this](const QJsonObject &arguments) {
            return edit(tr("Append clip"), [&]() {
                QString xml, error;
                if (!sourceXml(arguments, xml, error))
                    return failure(error);
                int track = 0;
                if (trackCount() > 0) {
                    if (arguments.contains("track") && !arguments.value("track").isNull()) {
                        if (!resolveTrack(arguments.value("track"), track, error))
                            return failure(error);
                    } else {
                        track = qBound(0, timeline()->currentTrack(), trackCount() - 1);
                    }
                    if (timeline()->isTrackLocked(track))
                        return failure(QStringLiteral("Track %1 is locked.").arg(trackCode(track)));
                }
                // An empty track holds one gap, which the new clip replaces.
                const int before = trackCount() ? realClipCount(track) : 0;
                timeline()->appendXml(track, xml);
                showProjectInPlayer();
                if (track >= trackCount() || realClipCount(track) <= before)
                    return failure(QStringLiteral("Shotcut could not append the clip."));
                const int clip = clipCountOf(track) - 1;
                return Mcp::ToolResult::success(
                    QJsonObject{{"track", track}, {"clip", clipJson(track, clip)}});
            });
        });

    auto placeClip = [this, add](const char *name, bool insert) {
        add(name,
            insert ? tr("Insert clip") : tr("Overwrite clip"),
            insert ? QStringLiteral(
                "Inserts a clip into a track at a time, moving the later clips of that track "
                "to the right (ripple), from the playlist (playlist_index), a file (path) or a "
                "media id (media).")
                   : QStringLiteral(
                       "Places a clip on a track at a time, replacing what is there (the other "
                       "clips do not move), from the playlist (playlist_index), a file (path) "
                       "or a media id (media)."),
            R"json({"type": "object",
                    "properties": {
                      "track": {"type": ["integer", "string"], "description": "Track index or code (V1, A1...)."},
                      "position": {"type": ["number", "string"], "description": "Seconds or timecode."},
                      "playlist_index": {"type": "integer", "minimum": 0,
                        "description": "A playlist item (get_playlist)."},
                      "path": {"type": "string", "description": "Or a media file (absolute path)."},
                      "media": {"type": "string",
                        "description": "Or a media id (m1...) from get_timeline or get_playlist."}},
                    "required": ["track", "position"], "additionalProperties": false})json",
            editing(),
            [this, insert](const QJsonObject &arguments) {
                return edit(insert ? tr("Insert clip") : tr("Overwrite clip"), [&]() {
                    QString xml, error;
                    int track = -1, position = 0;
                    if (!MAIN.isMultitrackValid())
                        return failure(QStringLiteral(
                            "The timeline is empty: use append_clip for the first clip."));
                    if (!resolveTrack(arguments.value("track"), track, error)
                        || !parseTime(arguments.value("position"), position, error)
                        || !sourceXml(arguments, xml, error))
                        return failure(error);
                    if (timeline()->isTrackLocked(track))
                        return failure(QStringLiteral("Track %1 is locked.").arg(trackCode(track)));
                    showProjectInPlayer();
                    if (insert)
                        timeline()->insert(track, position, xml, false);
                    else
                        timeline()->overwrite(track, position, xml, false);
                    return Mcp::ToolResult::success(trackJson(track, true, false));
                });
            });
    };
    placeClip("insert_clip", true);
    placeClip("overwrite_clip", false);

    const char *clipProperties = R"json(
                  "track": {"type": ["integer", "string"], "description": "Track index or code (V1, A1...)."},
                  "clip": {"type": "integer", "minimum": 0, "description": "Clip index in the track (get_timeline)."},
                  "uuid": {"type": "string", "description": "Alternative to track and clip."})json";
    auto clipSchema = [clipProperties](const char *more, const char *required = nullptr) {
        QByteArray json = "{\"type\": \"object\", \"properties\": {";
        json += clipProperties;
        if (more && *more)
            json += QByteArray(",") + more;
        json += "}, \"additionalProperties\": false";
        if (required)
            json += QByteArray(", \"required\": ") + required;
        json += "}";
        return json;
    };
    // The clip tools share the clip properties; add() parses each schema at once.
    QList<QByteArray> schemas;

    schemas << clipSchema(R"json(
                  "position": {"type": ["number", "string"],
                    "description": "Timeline time inside the clip; default: the playhead."})json");
    add("split_clip",
        "Split clip",
        "Splits a timeline clip in two at a time (default: the playhead). Returns both parts.",
        schemas.last().constData(),
        editing(),
        [this](const QJsonObject &arguments) {
            return edit(tr("Split clip"), [&]() {
                int track = -1, clip = -1;
                QString error;
                if (!resolveClip(arguments, track, clip, error))
                    return failure(error);
                int position = timeline()->position();
                if (arguments.contains("position") && !arguments.value("position").isNull()
                    && !parseTime(arguments.value("position"), position, error))
                    return failure(error);
                const auto index = clipModelIndex(track, clip);
                const int start = index.data(MultitrackModel::StartRole).toInt();
                const int end = start + index.data(MultitrackModel::DurationRole).toInt();
                if (position <= start || position >= end)
                    return failure(QStringLiteral("The split point must be inside the clip, "
                                                  "between %1 and %2 seconds.")
                                       .arg(secondsOf(start))
                                       .arg(secondsOf(end)));
                showProjectInPlayer();
                if (!timeline()->split(track, clip, position))
                    return failure(QStringLiteral("Shotcut could not split this clip."));
                return Mcp::ToolResult::success(
                    QJsonObject{{"track", track},
                                {"clips",
                                 QJsonArray{clipJson(track, clip), clipJson(track, clip + 1)}}});
            });
        });

    schemas << clipSchema(R"json(
                  "ripple": {"type": "boolean",
                    "description": "true (default): later clips move left to fill the gap; false: leave a gap."})json");
    add("remove_clip",
        "Remove clip",
        "Removes a clip from the timeline. By default the later clips of the track move "
        "left (ripple delete); with ripple false a gap is left (lift).",
        schemas.last().constData(),
        editing(),
        [this](const QJsonObject &arguments) {
            return edit(tr("Remove clip"), [&]() {
                int track = -1, clip = -1;
                QString error;
                if (!resolveClip(arguments, track, clip, error))
                    return failure(error);
                if (timeline()->isTrackLocked(track))
                    return failure(QStringLiteral("Track %1 is locked.").arg(trackCode(track)));
                showProjectInPlayer();
                const int before = clipCountOf(track);
                const auto name = clipJson(track, clip).value("name").toString();
                if (arguments.value("ripple").toBool(true))
                    timeline()->remove(track, clip);
                else
                    timeline()->lift(track, clip);
                if (clipCountOf(track) == before && !isBlank(track, clip))
                    return failure(QStringLiteral("Shotcut could not remove the clip."));
                return Mcp::ToolResult::success(
                    QJsonObject{{"removed", name}, {"track", trackJson(track, true, false)}});
            });
        });

    schemas << clipSchema(R"json(
                  "position": {"type": ["number", "string"], "description": "New start time (seconds or timecode)."},
                  "to_track": {"type": ["integer", "string"], "description": "Destination track; default: the same track."},
                  "ripple": {"type": "boolean", "description": "Move the later clips too (default false)."})json",
                          "[\"position\"]");
    add("move_clip",
        "Move clip",
        "Moves a timeline clip to a new start time and optionally to another track, like "
        "dragging it. Overlapping clips on the destination are overwritten.",
        schemas.last().constData(),
        editing(),
        [this](const QJsonObject &arguments) {
            return edit(tr("Move clip"), [&]() {
                int track = -1, clip = -1, toTrack = -1, position = 0;
                QString error;
                if (!resolveClip(arguments, track, clip, error)
                    || !parseTime(arguments.value("position"), position, error))
                    return failure(error);
                toTrack = track;
                if (arguments.contains("to_track") && !arguments.value("to_track").isNull()
                    && !resolveTrack(arguments.value("to_track"), toTrack, error))
                    return failure(error);
                if (timeline()->isTrackLocked(track) || timeline()->isTrackLocked(toTrack))
                    return failure(QStringLiteral("The track is locked."));
                const auto uuid = clipUuid(track, clip);
                showProjectInPlayer();
                timeline()->setSelection(QList<QPoint>() << QPoint(clip, track));
                timeline()->flushSelection();
                if (!timeline()->moveClip(track,
                                          toTrack,
                                          clip,
                                          position,
                                          arguments.value("ripple").toBool()))
                    return failure(QStringLiteral("Shotcut refused the move (for example because "
                                                  "of a transition or a locked track)."));
                // The move is committed by a queued call; run it now, inside this step.
                QCoreApplication::sendPostedEvents(timeline(), QEvent::MetaCall);
                QJsonObject result{{"track", trackJson(toTrack, true, false)}};
                int newTrack = toTrack;
                int newClip = clipStartingAt(toTrack, position);
                if (newClip < 0 && !uuid.isEmpty()
                    && !multitrack()->findClipByUuid(QUuid(uuid), newTrack, newClip))
                    newClip = -1;
                if (newClip >= 0)
                    result["moved"] = QJsonObject{{"track", newTrack},
                                                  {"clip", clipJson(newTrack, newClip)}};
                return Mcp::ToolResult::success(result);
            });
        });

    schemas << clipSchema(R"json(
                  "trim_start": {"type": ["number", "string"],
                    "description": "Time to remove from the start (seconds or timecode); negative extends the clip."},
                  "trim_end": {"type": ["number", "string"],
                    "description": "Time to remove from the end; negative extends the clip."},
                  "ripple": {"type": "boolean", "description": "Move the later clips to follow (default false)."})json");
    add("trim_clip",
        "Trim clip",
        "Shortens or extends a timeline clip at its start and/or end, like dragging its "
        "edges. Positive values remove time, negative values bring back hidden media.",
        schemas.last().constData(),
        editing(),
        [this](const QJsonObject &arguments) {
            return edit(tr("Trim clip"), [&]() {
                int track = -1, clip = -1, trimStart = 0, trimEnd = 0;
                QString error;
                if (!resolveClip(arguments, track, clip, error))
                    return failure(error);
                if (arguments.contains("trim_start") && !arguments.value("trim_start").isNull()
                    && !parseTime(arguments.value("trim_start"), trimStart, error, true))
                    return failure(error);
                if (arguments.contains("trim_end") && !arguments.value("trim_end").isNull()
                    && !parseTime(arguments.value("trim_end"), trimEnd, error, true))
                    return failure(error);
                if (!trimStart && !trimEnd)
                    return failure(QStringLiteral("Pass trim_start and/or trim_end."));
                if (timeline()->isTrackLocked(track))
                    return failure(QStringLiteral("Track %1 is locked.").arg(trackCode(track)));
                const bool ripple = arguments.value("ripple").toBool();
                const auto uuid = clipUuid(track, clip);
                const int start
                    = clipModelIndex(track, clip).data(MultitrackModel::StartRole).toInt();
                showProjectInPlayer();
                // The end first: trimming the start without ripple adds a gap before the
                // clip, which changes its index.
                if (trimEnd) {
                    if (!timeline()->trimClipOut(track, clip, trimEnd, ripple, false))
                        return failure(QStringLiteral("Shotcut could not trim the end."));
                    multitrack()->notifyClipOut(track, clip);
                    timeline()->commitTrimCommand();
                }
                if (trimStart) {
                    if (!timeline()->trimClipIn(track, clip, clip, trimStart, ripple, false))
                        return failure(QStringLiteral("Shotcut could not trim the start."));
                    multitrack()->notifyClipIn(track, clip);
                    timeline()->commitTrimCommand();
                }
                // Without ripple, trimming the start moves it later and adds a gap before it.
                int newTrack = track;
                int newClip = clipStartingAt(track, ripple ? start : start + trimStart);
                if (newClip < 0 && !uuid.isEmpty()
                    && !multitrack()->findClipByUuid(QUuid(uuid), newTrack, newClip))
                    newClip = -1;
                if (newClip < 0)
                    return Mcp::ToolResult::success(trackJson(track, true, false));
                return Mcp::ToolResult::success(
                    QJsonObject{{"track", newTrack}, {"clip", clipJson(newTrack, newClip)}});
            });
        });

    schemas << clipSchema(R"json(
                  "fade_in": {"type": ["number", "string"], "description": "Fade-in duration; 0 removes it."},
                  "fade_out": {"type": ["number", "string"], "description": "Fade-out duration; 0 removes it."})json");
    add("set_fade",
        "Set fade",
        "Sets the fade-in and/or fade-out of a timeline clip (video fades to black, audio "
        "fades volume), like dragging the fade handles.",
        schemas.last().constData(),
        editing(true),
        [this](const QJsonObject &arguments) {
            return edit(tr("Set fade"), [&]() {
                int track = -1, clip = -1, fadeIn = -1, fadeOut = -1;
                QString error;
                if (!resolveClip(arguments, track, clip, error))
                    return failure(error);
                if (arguments.contains("fade_in") && !arguments.value("fade_in").isNull()
                    && !parseTime(arguments.value("fade_in"), fadeIn, error))
                    return failure(error);
                if (arguments.contains("fade_out") && !arguments.value("fade_out").isNull()
                    && !parseTime(arguments.value("fade_out"), fadeOut, error))
                    return failure(error);
                if (fadeIn < 0 && fadeOut < 0)
                    return failure(QStringLiteral("Pass fade_in and/or fade_out."));
                if (timeline()->isTrackLocked(track))
                    return failure(QStringLiteral("Track %1 is locked.").arg(trackCode(track)));
                const int duration
                    = clipModelIndex(track, clip).data(MultitrackModel::DurationRole).toInt();
                if (qMax(fadeIn, 0) + qMax(fadeOut, 0) > duration)
                    return failure(QStringLiteral("The fades are longer than the clip (%1 s).")
                                       .arg(secondsOf(duration)));
                showProjectInPlayer();
                if (fadeIn >= 0)
                    timeline()->fadeIn(track, clip, fadeIn);
                if (fadeOut >= 0)
                    timeline()->fadeOut(track, clip, fadeOut);
                return Mcp::ToolResult::success(
                    QJsonObject{{"track", track}, {"clip", clipJson(track, clip)}});
            });
        });

    add("add_track",
        "Add track",
        "Adds a video track (above the others) or an audio track (below the others).",
        R"json({"type": "object",
                "properties": {"type": {"type": "string", "enum": ["video", "audio"]}},
                "required": ["type"], "additionalProperties": false})json",
        editing(),
        [this](const QJsonObject &arguments) {
            const bool audio = arguments.value("type").toString() == QLatin1String("audio");
            return edit(audio ? tr("Add audio track") : tr("Add video track"), [&]() {
                showProjectInPlayer();
                const int track = audio ? timeline()->addAudioTrack() : timeline()->addVideoTrack();
                if (track < 0 || track >= trackCount())
                    return failure(QStringLiteral("Shotcut could not add the track."));
                return Mcp::ToolResult::success(
                    QJsonObject{{"track", trackJson(track, false, false)},
                                {"tracks", trackCodes().join(", ")}});
            });
        });

    add("set_track",
        "Set track",
        "Renames a track or changes its mute, hidden (video tracks) or locked state.",
        R"json({"type": "object",
                "properties": {
                  "track": {"type": ["integer", "string"], "description": "Track index or code (V1, A1...)."},
                  "name": {"type": "string"},
                  "muted": {"type": "boolean"},
                  "hidden": {"type": "boolean"},
                  "locked": {"type": "boolean"}},
                "required": ["track"], "additionalProperties": false})json",
        editing(true),
        [this](const QJsonObject &arguments) {
            return edit(tr("Change track"), [&]() {
                int track = -1;
                QString error;
                if (!resolveTrack(arguments.value("track"), track, error))
                    return failure(error);
                const auto index = multitrack()->index(track);
                if (arguments.contains("name") && !arguments.value("name").isNull())
                    timeline()->setTrackName(track, arguments.value("name").toString());
                if (arguments.contains("muted") && !arguments.value("muted").isNull()
                    && index.data(MultitrackModel::IsMuteRole).toBool()
                           != arguments.value("muted").toBool())
                    timeline()->toggleTrackMute(track);
                if (arguments.contains("hidden") && !arguments.value("hidden").isNull()) {
                    if (index.data(MultitrackModel::IsAudioRole).toBool())
                        return failure(QStringLiteral("Audio tracks cannot be hidden; mute them."));
                    if (index.data(MultitrackModel::IsHiddenRole).toBool()
                        != arguments.value("hidden").toBool())
                        timeline()->toggleTrackHidden(track);
                }
                if (arguments.contains("locked") && !arguments.value("locked").isNull())
                    timeline()->setTrackLock(track, arguments.value("locked").toBool());
                return Mcp::ToolResult::success(trackJson(track, false, false));
            });
        });

    add("select_clips",
        "Select clips",
        "Selects timeline clips, like clicking them (an empty list clears the selection). "
        "Other tools and actions such as timelineCopyAction work on the selection.",
        R"json({"type": "object",
                "properties": {"clips": {"type": "array",
                  "items": {"type": "object",
                    "properties": {
                      "track": {"type": ["integer", "string"]},
                      "clip": {"type": "integer", "minimum": 0}},
                    "required": ["track", "clip"]}}},
                "required": ["clips"], "additionalProperties": false})json",
        editing(true),
        [this](const QJsonObject &arguments) {
            return run([&]() {
                QList<QPoint> points;
                for (const auto &value : arguments.value("clips").toArray()) {
                    int track = -1, clip = -1;
                    QString error;
                    if (!resolveClip(value.toObject(), track, clip, error))
                        return failure(error);
                    points << QPoint(clip, track);
                }
                showProjectInPlayer();
                if (!points.isEmpty())
                    timeline()->setCurrentTrack(points.first().y());
                timeline()->setSelection(points);
                timeline()->flushSelection();
                QJsonArray selection;
                for (const auto &point : timeline()->selection())
                    selection.append(QJsonObject{{"track", point.y()},
                                                 {"clip", clipJson(point.y(), point.x())}});
                return Mcp::ToolResult::success(QJsonObject{{"selection", selection}});
            });
        });

    // --- Filters -----------------------------------------------------------------------

    schemas << clipSchema(R"json(
                  "filter_id": {"type": "string", "description": "An id from list_filters."},
                  "parameters": {"type": "object",
                    "description": "Optional MLT properties to set, such as {\"level\": 1.5}."})json",
                          "[\"filter_id\"]");
    add("add_filter",
        "Add filter",
        "Adds a filter (from list_filters) to a timeline clip, like \"+\" in the Filters "
        "panel, which then shows it with its default settings. parameters sets MLT "
        "properties of the new filter (see get_clip_filters for their names).",
        schemas.last().constData(),
        editing(),
        [this](const QJsonObject &arguments) {
            return edit(tr("Add filter"), [&]() {
                int track = -1, clip = -1;
                QString error;
                if (!resolveClip(arguments, track, clip, error))
                    return failure(error);
                QmlMetadata *meta = filters()->metadata(arguments.value("filter_id").toString());
                if (!meta)
                    return failure(QStringLiteral("Unknown filter id \"%1\": use list_filters.")
                                       .arg(arguments.value("filter_id").toString()));
                if (!loadClipFilters(track, clip, error))
                    return failure(error);
                // The Filters panel shows the new filter and its interface sets the defaults.
                MAIN.onFiltersDockTriggered(true);
                auto model = filters()->attachedModel();
                const int row = model->add(meta);
                if (row < 0)
                    return failure(QStringLiteral("Shotcut could not add %1 (some filters can "
                                                  "only be added once).")
                                       .arg(meta->name()));
                filters()->setCurrentFilter(row);
                QCoreApplication::processEvents();
                QmlFilter *filter = filters()->currentFilter();
                if (filter && filter->service().is_valid()) {
                    if (!model->isSourceClip())
                        filter->startUndoTracking();
                    const auto parameters = arguments.value("parameters").toObject();
                    if (!parameters.isEmpty()) {
                        filter->startUndoParameterCommand(meta->name());
                        const bool ok = setFilterParameters(filter, parameters, error);
                        filter->endUndoCommand();
                        if (!ok)
                            return failure(error);
                    }
                }
                return Mcp::ToolResult::success(QJsonObject{{"track", track},
                                                            {"clip", clip},
                                                            {"filter", filterJson(row)},
                                                            {"filters", model->rowCount()}});
            });
        });

    schemas << clipSchema(R"json(
                  "filter_index": {"type": "integer", "minimum": 0, "description": "From get_clip_filters."},
                  "parameters": {"type": "object", "description": "MLT properties to set, such as {\"level\": 1.5}."})json",
                          "[\"filter_index\", \"parameters\"]");
    add("set_filter_param",
        "Set filter parameters",
        "Changes parameters (MLT properties) of a filter of a timeline clip, as one undo "
        "step. get_clip_filters lists the current values.",
        schemas.last().constData(),
        editing(true),
        [this](const QJsonObject &arguments) {
            return edit(tr("Change filter"), [&]() {
                int track = -1, clip = -1, row = -1;
                QString error;
                if (!resolveClip(arguments, track, clip, error)
                    || !loadClipFilters(track, clip, error)
                    || !resolveFilterRow(arguments, row, error))
                    return failure(error);
                const auto parameters = arguments.value("parameters").toObject();
                if (parameters.isEmpty())
                    return failure(QStringLiteral("Pass at least one parameter."));
                filters()->setCurrentFilter(row);
                QmlFilter *filter = filters()->currentFilter();
                if (!filter || !filter->service().is_valid())
                    return failure(QStringLiteral("Could not edit the filter."));
                filter->startUndoParameterCommand(filters()->attachedModel()->name(row));
                const bool ok = setFilterParameters(filter, parameters, error);
                filter->endUndoCommand();
                if (!ok)
                    return failure(error);
                return Mcp::ToolResult::success(
                    QJsonObject{{"track", track}, {"clip", clip}, {"filter", filterJson(row)}});
            });
        });

    schemas << clipSchema(R"json(
                  "filter_index": {"type": "integer", "minimum": 0, "description": "From get_clip_filters."},
                  "enabled": {"type": "boolean"})json",
                          "[\"filter_index\", \"enabled\"]");
    add("set_filter_enabled",
        "Enable or disable filter",
        "Turns a filter of a timeline clip on or off, like its switch in the Inspector.",
        schemas.last().constData(),
        editing(true),
        [this](const QJsonObject &arguments) {
            return edit(tr("Enable filter"), [&]() {
                int track = -1, clip = -1, row = -1;
                QString error;
                if (!resolveClip(arguments, track, clip, error)
                    || !loadClipFilters(track, clip, error)
                    || !resolveFilterRow(arguments, row, error))
                    return failure(error);
                auto model = filters()->attachedModel();
                const bool enabled = arguments.value("enabled").toBool();
                if ((model->data(model->index(row), Qt::CheckStateRole).toInt() == Qt::Checked)
                    != enabled)
                    model->setData(model->index(row),
                                   enabled ? Qt::Checked : Qt::Unchecked,
                                   Qt::CheckStateRole);
                return Mcp::ToolResult::success(
                    QJsonObject{{"track", track}, {"clip", clip}, {"filter", filterJson(row)}});
            });
        });

    schemas << clipSchema(R"json(
                  "filter_index": {"type": "integer", "minimum": 0, "description": "From get_clip_filters."})json",
                          "[\"filter_index\"]");
    add("remove_filter",
        "Remove filter",
        "Removes a filter from a timeline clip.",
        schemas.last().constData(),
        editing(),
        [this](const QJsonObject &arguments) {
            return edit(tr("Remove filter"), [&]() {
                int track = -1, clip = -1, row = -1;
                QString error;
                if (!resolveClip(arguments, track, clip, error)
                    || !loadClipFilters(track, clip, error)
                    || !resolveFilterRow(arguments, row, error))
                    return failure(error);
                auto model = filters()->attachedModel();
                const auto name = model->name(row);
                model->remove(row);
                return Mcp::ToolResult::success(
                    QJsonObject{{"removed", name}, {"filters", clipFiltersJson()}});
            });
        });
}
