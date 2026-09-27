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

#ifndef SCRUBBAR_H
#define SCRUBBAR_H

#include <QColor>
#include <QWidget>

/*!
  \class ScrubBar
  \brief The player progress bar.

  A thin track shows the play position with a filled progress segment and a
  round drag handle. The in and out points are drawn as brackets that can be
  dragged, and playlist markers and the loop range are drawn on the track.
  Colors can be themed from a style sheet (qproperty-trackColor, etc.).
*/
class ScrubBar : public QWidget
{
    Q_OBJECT
    Q_PROPERTY(QColor trackColor READ trackColor WRITE setTrackColor)
    Q_PROPERTY(QColor progressColor READ progressColor WRITE setProgressColor)
    Q_PROPERTY(QColor handleColor READ handleColor WRITE setHandleColor)
    Q_PROPERTY(QColor selectionColor READ selectionColor WRITE setSelectionColor)
    Q_PROPERTY(QColor markerColor READ markerColor WRITE setMarkerColor)
    Q_PROPERTY(QColor loopColor READ loopColor WRITE setLoopColor)

    enum controls { CONTROL_NONE, CONTROL_HEAD, CONTROL_IN, CONTROL_OUT };

public:
    explicit ScrubBar(QWidget *parent = 0);

    virtual void mousePressEvent(QMouseEvent *event);
    virtual void mouseReleaseEvent(QMouseEvent *event);
    virtual void mouseMoveEvent(QMouseEvent *event);
    QSize sizeHint() const override;
    void setScale(int maximum);
    void setFramerate(double fps);
    int position() const;
    void setInPoint(int in);
    void setOutPoint(int out);
    void setMarkers(const QList<int> &);
    QList<int> markers() const { return m_markers; }
    void setMargin(int margin) { m_margin = margin; }
    void setLoopRange(int start, int end);

    QColor trackColor() const;
    void setTrackColor(const QColor &color);
    QColor progressColor() const;
    void setProgressColor(const QColor &color);
    QColor handleColor() const;
    void setHandleColor(const QColor &color);
    QColor selectionColor() const;
    void setSelectionColor(const QColor &color);
    QColor markerColor() const;
    void setMarkerColor(const QColor &color);
    QColor loopColor() const;
    void setLoopColor(const QColor &color);

signals:
    void paused(int);
    void seeked(int);
    void inChanged(int);
    void outChanged(int);

public slots:
    bool onSeek(int value);

protected:
    virtual void paintEvent(QPaintEvent *e);
    virtual void resizeEvent(QResizeEvent *);
    virtual bool event(QEvent *event);
    void leaveEvent(QEvent *event) override;

private:
    int m_head;
    double m_scale;
    double m_fps;
    int m_max;
    int m_in;
    int m_out;
    int m_margin;
    enum controls m_activeControl;
    QPixmap m_pixmap;
    QList<int> m_markers;
    int m_loopStart;
    int m_loopEnd;
    bool m_handleHovered;
    QColor m_trackColor;
    QColor m_progressColor;
    QColor m_handleColor;
    QColor m_selectionColor;
    QColor m_markerColor;
    QColor m_loopColor;

    void updatePixmap();
    int trackTop() const;
    int headX() const;
};

#endif // SCRUBBAR_H
