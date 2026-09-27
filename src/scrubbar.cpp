/*
 * Copyright (c) 2011-2026 Meltytech, LLC
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

#include "scrubbar.h"

#include "mltcontroller.h"
#include "settings.h"

#include <QToolTip>
#include <QtWidgets>

static constexpr int kBarHeight = 26;    /// the preferred height of the widget
static constexpr int kTrackHeight = 4;   /// the height of the progress track
static constexpr int kHandleSize = 12;   /// the diameter of the drag handle
static constexpr int kHaloWidth = 4;     /// the hover ring around the handle
static constexpr int kBracketExtent = 6; /// how far the in and out brackets reach past the track
#ifndef CLAMP
#define CLAMP(x, min, max) (((x) < (min)) ? (min) : ((x) > (max)) ? (max) : (x))
#endif

ScrubBar::ScrubBar(QWidget *parent)
    : QWidget(parent)
    , m_head(-1)
    , m_scale(-1)
    , m_fps(25)
    , m_max(1)
    , m_in(-1)
    , m_out(-1)
    , m_margin(14) /// left and right margins
    , m_activeControl(CONTROL_NONE)
    , m_loopStart(-1)
    , m_loopEnd(-1)
    , m_handleHovered(false)
{
    setMouseTracking(true);
    setMinimumHeight(kBarHeight);
    setWhatsThis("https://forum.shotcut.org/t/trimming-clips/49216/1");
}

QSize ScrubBar::sizeHint() const
{
    return QSize(200, kBarHeight);
}

void ScrubBar::setScale(int maximum)
{
    m_max = maximum;
    /// m_scale is the pixels per frame ratio
    m_scale = m_max > 0 ? (double) (width() - 2 * m_margin) / (double) m_max : -1;
    if (m_scale == 0)
        m_scale = -1;
    m_head = -1;
    updatePixmap();
}

void ScrubBar::setFramerate(double fps)
{
    m_fps = fps;
}

int ScrubBar::position() const
{
    return m_head;
}

void ScrubBar::setInPoint(int in)
{
    m_in = qMax(in, -1);
    updatePixmap();
    emit inChanged(in);
}

void ScrubBar::setOutPoint(int out)
{
    m_out = qMin(out, m_max);
    updatePixmap();
    emit outChanged(out);
}

void ScrubBar::setMarkers(const QList<int> &list)
{
    m_markers = list;
    updatePixmap();
}

void ScrubBar::setLoopRange(int start, int end)
{
    m_loopStart = start;
    m_loopEnd = end;
    updatePixmap();
}

QColor ScrubBar::trackColor() const
{
    return m_trackColor.isValid() ? m_trackColor : palette().color(QPalette::Mid);
}

void ScrubBar::setTrackColor(const QColor &color)
{
    m_trackColor = color;
    updatePixmap();
}

QColor ScrubBar::progressColor() const
{
    return m_progressColor.isValid() ? m_progressColor : palette().color(QPalette::Highlight);
}

void ScrubBar::setProgressColor(const QColor &color)
{
    m_progressColor = color;
    update();
}

QColor ScrubBar::handleColor() const
{
    return m_handleColor.isValid() ? m_handleColor : QColor(Qt::white);
}

void ScrubBar::setHandleColor(const QColor &color)
{
    m_handleColor = color;
    update();
}

QColor ScrubBar::selectionColor() const
{
    return m_selectionColor.isValid() ? m_selectionColor : palette().color(QPalette::Text);
}

void ScrubBar::setSelectionColor(const QColor &color)
{
    m_selectionColor = color;
    updatePixmap();
}

QColor ScrubBar::markerColor() const
{
    return m_markerColor.isValid() ? m_markerColor : palette().color(QPalette::Highlight);
}

void ScrubBar::setMarkerColor(const QColor &color)
{
    m_markerColor = color;
    updatePixmap();
}

QColor ScrubBar::loopColor() const
{
    if (m_loopColor.isValid())
        return m_loopColor;
    QColor color = palette().color(QPalette::Highlight);
    color.setAlphaF(0.5);
    return color;
}

void ScrubBar::setLoopColor(const QColor &color)
{
    m_loopColor = color;
    updatePixmap();
}

int ScrubBar::trackTop() const
{
    return (height() - kTrackHeight) / 2;
}

int ScrubBar::headX() const
{
    return m_margin + (m_scale > 0 ? qRound(m_head * m_scale) : 0);
}

void ScrubBar::mousePressEvent(QMouseEvent *event)
{
    int x = event->position().x() - m_margin;
    int in = m_in * m_scale;
    int out = m_out * m_scale;
    int pos = CLAMP(x / m_scale, 0, m_max);

    if (m_in > -1 && m_out > -1) {
        if (x >= in - 12 && x <= in + 6) {
            m_activeControl = CONTROL_IN;
            setInPoint(pos);
        } else if (x >= out - 6 && x <= out + 12) {
            m_activeControl = CONTROL_OUT;
            setOutPoint(pos);
        }
    }
    if (m_head > -1) {
        if (m_activeControl == CONTROL_NONE) {
            m_activeControl = CONTROL_HEAD;
            m_head = pos;
            update();
        }
    }
    if (m_activeControl >= CONTROL_IN && !Settings.playerPauseAfterSeek())
        emit paused(pos);
    emit seeked(pos);
}

void ScrubBar::mouseReleaseEvent(QMouseEvent *event)
{
    Q_UNUSED(event)
    m_activeControl = CONTROL_NONE;
    update();
}

void ScrubBar::mouseMoveEvent(QMouseEvent *event)
{
    int x = event->position().x() - m_margin;
    int pos = CLAMP(x / m_scale, 0, m_max);

    if (event->buttons() & Qt::LeftButton) {
        if (m_activeControl == CONTROL_IN)
            setInPoint(pos);
        else if (m_activeControl == CONTROL_OUT)
            setOutPoint(pos);
        else if (m_activeControl == CONTROL_HEAD) {
            m_head = pos;
            update();
        }
        if (m_activeControl >= CONTROL_IN && !Settings.playerPauseAfterSeek())
            emit paused(pos);
        emit seeked(pos);
    } else if (event->buttons() == Qt::NoButton) {
        const bool hovered = m_head >= 0
                             && qAbs(event->position().x() - headX())
                                    <= kHandleSize / 2 + kHaloWidth;
        if (hovered != m_handleHovered) {
            m_handleHovered = hovered;
            update();
        }
        if (MLT.producer()) {
            QString text = QString::fromLatin1(
                MLT.producer()->frames_to_time(pos, Settings.timeFormat()));
            QToolTip::showText(event->globalPosition().toPoint(), text);
        }
    }
}

void ScrubBar::leaveEvent(QEvent *event)
{
    if (m_handleHovered) {
        m_handleHovered = false;
        update();
    }
    QWidget::leaveEvent(event);
}

bool ScrubBar::onSeek(int value)
{
    if (m_activeControl != CONTROL_HEAD)
        m_head = value;
    update();
    return true;
}

void ScrubBar::paintEvent(QPaintEvent *e)
{
    QPainter p(this);
    p.setClipRect(e->rect());
    p.drawPixmap(0, 0, m_pixmap);

    if (!isEnabled() || m_scale <= 0 || m_head < 0)
        return;

    // Progress from the start to the play head, then the round drag handle.
    p.setRenderHint(QPainter::Antialiasing);
    const qreal top = trackTop();
    const qreal x = headX();
    p.setPen(Qt::NoPen);
    p.setBrush(progressColor());
    p.drawRoundedRect(QRectF(m_margin, top, qMax(0.0, x - m_margin), kTrackHeight),
                      kTrackHeight / 2.0,
                      kTrackHeight / 2.0);

    const QPointF center(x, top + kTrackHeight / 2.0);
    const bool dragging = m_activeControl == CONTROL_HEAD;
    if (m_handleHovered || dragging) {
        QColor halo = progressColor();
        halo.setAlphaF(0.18);
        p.setBrush(halo);
        p.drawEllipse(center, kHandleSize / 2.0 + kHaloWidth, kHandleSize / 2.0 + kHaloWidth);
    }
    p.setPen(QPen(QColor(0, 0, 0, 60), 1));
    p.setBrush(dragging ? progressColor() : handleColor());
    p.drawEllipse(center, kHandleSize / 2.0, kHandleSize / 2.0);
}

void ScrubBar::resizeEvent(QResizeEvent *)
{
    setScale(m_max);
}

bool ScrubBar::event(QEvent *event)
{
    QWidget::event(event);
    if (event->type() == QEvent::PaletteChange || event->type() == QEvent::StyleChange
        || event->type() == QEvent::EnabledChange)
        updatePixmap();
    return false;
}

void ScrubBar::updatePixmap()
{
    const auto ratio = devicePixelRatioF();
    m_pixmap = QPixmap(qMax(1, qRound(width() * ratio)), qMax(1, qRound(height() * ratio)));
    m_pixmap.setDevicePixelRatio(ratio);
    m_pixmap.fill(Qt::transparent);
    QPainter p(&m_pixmap);
    p.setRenderHint(QPainter::Antialiasing);
    p.setPen(Qt::NoPen);

    // The track
    const qreal top = trackTop();
    const qreal left = m_margin;
    const qreal trackWidth = qMax(0, width() - 2 * m_margin);
    QColor track = trackColor();
    if (!isEnabled())
        track.setAlphaF(track.alphaF() * 0.5);
    p.setBrush(track);
    p.drawRoundedRect(QRectF(left, top, trackWidth, kTrackHeight),
                      kTrackHeight / 2.0,
                      kTrackHeight / 2.0);

    if (!isEnabled() || m_scale <= 0) {
        p.end();
        update();
        return;
    }

    // selected region
    if (m_in > -1 && m_out > m_in) {
        QColor band = selectionColor();
        if (band.alpha() == 255)
            band.setAlphaF(0.35);
        p.fillRect(QRectF(left + m_in * m_scale, top, (m_out - m_in) * m_scale, kTrackHeight), band);
    }

    // draw markers
    if (m_in < 0 && m_out < 0 && !m_markers.isEmpty()) {
        QFont font = this->font();
        font.setPointSizeF(qMax(6.0, font.pointSizeF() * 0.75));
        p.setFont(font);
        const QFontMetricsF metrics(font);
        int i = 1;
        foreach (int pos, m_markers) {
            const qreal x = left + pos * m_scale;
            if (x < 0)
                continue;
            p.fillRect(QRectF(x - 1, top - 3, 2, kTrackHeight + 6), markerColor());
            const QString s = QString::number(i++);
            p.setPen(markerColor());
            p.drawText(QPointF(x - metrics.horizontalAdvance(s) / 2.0, top - 4), s);
            p.setPen(Qt::NoPen);
        }
    }

    // draw loop range
    if (m_loopStart > -1 && m_loopEnd > -1) {
        p.fillRect(QRectF(left + m_loopStart * m_scale,
                          top + kTrackHeight + 3,
                          (m_loopEnd - m_loopStart) * m_scale,
                          2),
                   loopColor());
    }

    // draw in and out points as brackets
    QColor bracket = selectionColor();
    bracket.setAlpha(255);
    const qreal bracketTop = top - kBracketExtent;
    const qreal bracketHeight = kTrackHeight + 2 * kBracketExtent;
    if (m_in > -1) {
        const qreal x = left + m_in * m_scale;
        p.fillRect(QRectF(x - 1, bracketTop, 2, bracketHeight), bracket);
        p.fillRect(QRectF(x - 1, bracketTop, 4, 2), bracket);
        p.fillRect(QRectF(x - 1, bracketTop + bracketHeight - 2, 4, 2), bracket);
    }
    if (m_out > -1) {
        const qreal x = left + m_out * m_scale;
        p.fillRect(QRectF(x - 1, bracketTop, 2, bracketHeight), bracket);
        p.fillRect(QRectF(x - 3, bracketTop, 4, 2), bracket);
        p.fillRect(QRectF(x - 3, bracketTop + bracketHeight - 2, 4, 2), bracket);
    }

    p.end();
    update();
}
