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

#ifndef TRANSPORTPLAYBUTTON_H
#define TRANSPORTPLAYBUTTON_H

#include <QColor>
#include <QToolButton>

/*!
  \class TransportPlayButton
  \brief The round play/pause button of the player transport row.

  Use setDefaultAction() to bind it to the play/pause action: the button
  follows the action's icon, tool tip and enabled state. The icon glyph is
  painted in glyphColor on a filled circle of a fixed diameter (44 px by
  default). Colors default to the palette (Highlight and HighlightedText) and
  can be themed from a style sheet with qproperty-fillColor, and so on.
*/
class TransportPlayButton : public QToolButton
{
    Q_OBJECT
    Q_PROPERTY(QColor fillColor READ fillColor WRITE setFillColor)
    Q_PROPERTY(QColor hoverColor READ hoverColor WRITE setHoverColor)
    Q_PROPERTY(QColor pressedColor READ pressedColor WRITE setPressedColor)
    Q_PROPERTY(QColor glyphColor READ glyphColor WRITE setGlyphColor)
    Q_PROPERTY(QColor disabledFillColor READ disabledFillColor WRITE setDisabledFillColor)
    Q_PROPERTY(QColor disabledGlyphColor READ disabledGlyphColor WRITE setDisabledGlyphColor)
    Q_PROPERTY(int diameter READ diameter WRITE setDiameter)

public:
    explicit TransportPlayButton(QWidget *parent = nullptr);
    QSize sizeHint() const override;
    QSize minimumSizeHint() const override;
    int diameter() const { return m_diameter; }
    void setDiameter(int diameter);

    QColor fillColor() const;
    void setFillColor(const QColor &color);
    QColor hoverColor() const;
    void setHoverColor(const QColor &color);
    QColor pressedColor() const;
    void setPressedColor(const QColor &color);
    QColor glyphColor() const;
    void setGlyphColor(const QColor &color);
    QColor disabledFillColor() const;
    void setDisabledFillColor(const QColor &color);
    QColor disabledGlyphColor() const;
    void setDisabledGlyphColor(const QColor &color);

protected:
    void paintEvent(QPaintEvent *event) override;

private:
    QColor m_fillColor;
    QColor m_hoverColor;
    QColor m_pressedColor;
    QColor m_glyphColor;
    QColor m_disabledFillColor;
    QColor m_disabledGlyphColor;
    int m_diameter;
};

#endif // TRANSPORTPLAYBUTTON_H
