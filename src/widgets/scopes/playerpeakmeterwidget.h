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

#ifndef PLAYERPEAKMETERWIDGET_H
#define PLAYERPEAKMETERWIDGET_H

#include "scopewidget.h"

#include <QColor>
#include <QVector>

/*!
  \class PlayerPeakMeterWidget
  \brief A compact vertical peak meter embedded next to the player video.

  It shows one thin bar per audio channel (stereo by default) with a peak-hold
  line. The levels are computed in the scope thread like the Audio Peak Meter
  scope. Colors and bar width can be themed from a style sheet, for example
  qproperty-trackColor, qproperty-lowColor, qproperty-highColor and
  qproperty-barWidth.
*/
class PlayerPeakMeterWidget Q_DECL_FINAL : public ScopeWidget
{
    Q_OBJECT
    Q_PROPERTY(QColor trackColor READ trackColor WRITE setTrackColor)
    Q_PROPERTY(QColor lowColor READ lowColor WRITE setLowColor)
    Q_PROPERTY(QColor highColor READ highColor WRITE setHighColor)
    Q_PROPERTY(QColor peakColor READ peakColor WRITE setPeakColor)
    Q_PROPERTY(int barWidth READ barWidth WRITE setBarWidth)

public:
    explicit PlayerPeakMeterWidget();
    QString getTitle() Q_DECL_OVERRIDE;
    QSize sizeHint() const Q_DECL_OVERRIDE;
    QSize minimumSizeHint() const Q_DECL_OVERRIDE;

    QColor trackColor() const;
    void setTrackColor(const QColor &color);
    QColor lowColor() const;
    void setLowColor(const QColor &color);
    QColor highColor() const;
    void setHighColor(const QColor &color);
    QColor peakColor() const;
    void setPeakColor(const QColor &color);
    int barWidth() const { return m_barWidth; }
    void setBarWidth(int width);

public slots:
    //! Drops the displayed levels, for example when playback pauses.
    void clear();

protected:
    void paintEvent(QPaintEvent *) Q_DECL_OVERRIDE;

private:
    // Runs in the scope thread.
    void refreshScope(const QSize &size, bool full) Q_DECL_OVERRIDE;
    int channelCount() const;

    QVector<double> m_levels;
    QVector<double> m_peaks;
    QColor m_trackColor;
    QColor m_lowColor;
    QColor m_highColor;
    QColor m_peakColor;
    int m_barWidth;

private slots:
    void showLevels(const QVector<double> &levels);
};

#endif // PLAYERPEAKMETERWIDGET_H
