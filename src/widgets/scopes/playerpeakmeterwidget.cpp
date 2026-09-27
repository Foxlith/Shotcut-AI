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

#include "playerpeakmeterwidget.h"

#include "audiopeakmeterscopewidget.h"
#include "widgets/iecscale.h"

#include <QLinearGradient>
#include <QPainter>

static constexpr int kBarGap = 2;
static constexpr int kSidePadding = 2;
static constexpr double kPeakDecayDb = 0.2;
static constexpr double kSilenceDb = -100.0;

PlayerPeakMeterWidget::PlayerPeakMeterWidget()
    : ScopeWidget("PlayerPeakMeter")
    , m_barWidth(6)
{
    qRegisterMetaType<QVector<double>>("QVector<double>");
    setToolTip(tr("Audio Peak Meter"));
    setSizePolicy(QSizePolicy::Fixed, QSizePolicy::Expanding);
}

QString PlayerPeakMeterWidget::getTitle()
{
    return tr("Audio Peak Meter");
}

int PlayerPeakMeterWidget::channelCount() const
{
    return m_levels.isEmpty() ? 2 : m_levels.size();
}

QSize PlayerPeakMeterWidget::sizeHint() const
{
    const int channels = channelCount();
    return QSize(2 * kSidePadding + channels * m_barWidth + (channels - 1) * kBarGap, 160);
}

QSize PlayerPeakMeterWidget::minimumSizeHint() const
{
    return QSize(sizeHint().width(), 40);
}

QColor PlayerPeakMeterWidget::trackColor() const
{
    return m_trackColor.isValid() ? m_trackColor : palette().color(QPalette::AlternateBase);
}

void PlayerPeakMeterWidget::setTrackColor(const QColor &color)
{
    m_trackColor = color;
    update();
}

QColor PlayerPeakMeterWidget::lowColor() const
{
    return m_lowColor.isValid() ? m_lowColor : QColor(0x2B, 0xB5, 0x96);
}

void PlayerPeakMeterWidget::setLowColor(const QColor &color)
{
    m_lowColor = color;
    update();
}

QColor PlayerPeakMeterWidget::highColor() const
{
    return m_highColor.isValid() ? m_highColor : QColor(0xF5, 0xC5, 0x42);
}

void PlayerPeakMeterWidget::setHighColor(const QColor &color)
{
    m_highColor = color;
    update();
}

QColor PlayerPeakMeterWidget::peakColor() const
{
    return m_peakColor.isValid() ? m_peakColor : palette().color(QPalette::WindowText);
}

void PlayerPeakMeterWidget::setPeakColor(const QColor &color)
{
    m_peakColor = color;
    update();
}

void PlayerPeakMeterWidget::setBarWidth(int width)
{
    m_barWidth = qMax(1, width);
    updateGeometry();
    update();
}

void PlayerPeakMeterWidget::clear()
{
    for (auto &level : m_levels)
        level = kSilenceDb;
    for (auto &peak : m_peaks)
        peak = kSilenceDb;
    update();
}

void PlayerPeakMeterWidget::refreshScope(const QSize & /*size*/, bool /*full*/)
{
    SharedFrame frame;
    while (m_queue.count() > 0) {
        frame = m_queue.pop();
        const QVector<double> levels = AudioPeakMeterScopeWidget::peakLevels(frame);
        if (!levels.isEmpty()) {
            QMetaObject::invokeMethod(this,
                                      "showLevels",
                                      Qt::QueuedConnection,
                                      Q_ARG(const QVector<double> &, levels));
        }
    }
}

void PlayerPeakMeterWidget::showLevels(const QVector<double> &levels)
{
    const bool channelsChanged = levels.size() != m_levels.size();
    m_levels = levels;
    if (channelsChanged || m_peaks.size() != m_levels.size()) {
        m_peaks = m_levels;
        updateGeometry();
    } else {
        for (int i = 0; i < m_levels.size(); i++)
            m_peaks[i] = qMax(m_peaks[i] - kPeakDecayDb, m_levels[i]);
    }
    update();
}

void PlayerPeakMeterWidget::paintEvent(QPaintEvent *)
{
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing);
    p.setPen(Qt::NoPen);

    const int channels = channelCount();
    const int total = channels * m_barWidth + (channels - 1) * kBarGap;
    const qreal radius = m_barWidth / 3.0;
    const QRectF area((width() - total) / 2.0, 0, total, height());

    // Green for nominal levels, turning amber towards the top (about -6 dB).
    QLinearGradient gradient(0, area.bottom(), 0, area.top());
    gradient.setColorAt(0.0, lowColor());
    gradient.setColorAt(IEC_Scale(-18.0), lowColor());
    gradient.setColorAt(IEC_Scale(-6.0), highColor());
    gradient.setColorAt(1.0, highColor());

    qreal x = area.left();
    for (int c = 0; c < channels; ++c, x += m_barWidth + kBarGap) {
        const QRectF bar(x, area.top(), m_barWidth, area.height());
        p.setBrush(trackColor());
        p.drawRoundedRect(bar, radius, radius);

        const double level = c < m_levels.size() ? IEC_Scale(m_levels[c]) : 0.0;
        if (level > 0.0) {
            QRectF fill = bar;
            fill.setTop(bar.bottom() - level * bar.height());
            p.setBrush(gradient);
            p.drawRoundedRect(fill, radius, radius);
        }
        const double peak = c < m_peaks.size() ? IEC_Scale(m_peaks[c]) : 0.0;
        if (peak > 0.0) {
            const qreal y = bar.bottom() - peak * bar.height();
            p.fillRect(QRectF(x, qMax(bar.top(), y - 1.0), m_barWidth, 1.5), peakColor());
        }
    }
}
