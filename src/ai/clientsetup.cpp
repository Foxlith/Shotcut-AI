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

#include "clientsetup.h"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QSaveFile>

namespace ClientSetup {

static const char *kConfigName = "Claude/claude_desktop_config.json";

QStringList claudeDesktopConfigCandidates(const QString &configDir, const QString &localAppData)
{
    QStringList candidates;
    if (!localAppData.isEmpty()) {
        const auto local = QDir::cleanPath(QDir::fromNativeSeparators(localAppData));
        QDir packages(local + QStringLiteral("/Packages"));
        const auto names = packages.entryList(QStringList{QStringLiteral("Claude*")},
                                              QDir::Dirs | QDir::NoDotAndDotDot,
                                              QDir::Name);
        for (const auto &name : names)
            candidates << packages.absoluteFilePath(name + QStringLiteral("/LocalCache/Roaming/")
                                                    + QLatin1String(kConfigName));
    }
    if (!configDir.isEmpty())
        candidates << QDir::cleanPath(QDir::fromNativeSeparators(configDir)) + QLatin1Char('/')
                          + QLatin1String(kConfigName);
    return candidates;
}

QString chooseConfigFile(const QStringList &candidates)
{
    for (const auto &candidate : candidates)
        if (QFileInfo(candidate).isFile())
            return candidate;
    for (const auto &candidate : candidates)
        if (QFileInfo(candidate).dir().exists())
            return candidate;
    return candidates.isEmpty() ? QString() : candidates.last();
}

MergeResult mergeMcpServers(const QByteArray &existing,
                            const QJsonObject &servers,
                            QByteArray &output,
                            QString *error)
{
    output.clear();
    QJsonObject config;
    if (!existing.trimmed().isEmpty()) {
        QJsonParseError parseError;
        const auto document = QJsonDocument::fromJson(existing, &parseError);
        if (parseError.error != QJsonParseError::NoError || !document.isObject()) {
            if (error)
                *error = parseError.error != QJsonParseError::NoError
                             ? QStringLiteral("The file is not valid JSON: %1 (at character %2).")
                                   .arg(parseError.errorString())
                                   .arg(parseError.offset)
                             : QStringLiteral("The file is not a JSON object.");
            return MergeResult::Invalid;
        }
        config = document.object();
    }
    const auto current = config.value("mcpServers");
    if (!current.isUndefined() && !current.isObject()) {
        if (error)
            *error = QStringLiteral("\"mcpServers\" in the file is not an object.");
        return MergeResult::Invalid;
    }
    auto merged = current.toObject();
    bool changed = !config.contains("mcpServers");
    for (auto it = servers.constBegin(); it != servers.constEnd(); ++it) {
        if (merged.value(it.key()) != it.value()) {
            merged[it.key()] = it.value();
            changed = true;
        }
    }
    config["mcpServers"] = merged;
    output = QJsonDocument(config).toJson(QJsonDocument::Indented);
    return changed ? MergeResult::Changed : MergeResult::Unchanged;
}

bool writeMcpServers(const QString &path, const QJsonObject &servers, QString *error)
{
    QByteArray existing;
    const bool exists = QFileInfo(path).isFile();
    if (exists) {
        QFile file(path);
        if (!file.open(QIODevice::ReadOnly)) {
            if (error)
                *error = QStringLiteral("Cannot read %1: %2").arg(path, file.errorString());
            return false;
        }
        existing = file.readAll();
    }
    QByteArray output;
    QString problem;
    const auto result = mergeMcpServers(existing, servers, output, &problem);
    if (result == MergeResult::Invalid) {
        if (error)
            *error = QStringLiteral("%1 was left as it was. %2").arg(path, problem);
        return false;
    }
    if (result == MergeResult::Unchanged)
        return true;
    if (!QDir().mkpath(QFileInfo(path).absolutePath())) {
        if (error)
            *error = QStringLiteral("Cannot create the folder of %1.").arg(path);
        return false;
    }
    if (exists) {
        const auto backup = path + QStringLiteral(".bak");
        QFile::remove(backup);
        if (!QFile::copy(path, backup)) {
            if (error)
                *error = QStringLiteral("Cannot make the backup copy %1.").arg(backup);
            return false;
        }
    }
    QSaveFile file(path);
    if (!file.open(QIODevice::WriteOnly) || file.write(output) != output.size() || !file.commit()) {
        if (error)
            *error = QStringLiteral("Cannot write %1: %2").arg(path, file.errorString());
        return false;
    }
    return true;
}

} // namespace ClientSetup
