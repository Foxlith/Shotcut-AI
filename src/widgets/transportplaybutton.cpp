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

#include "transportplaybutton.h"

#include <QPainter>

TransportPlayButton::TransportPlayButton(QWidget *parent)
    : QToolButton(parent)
    , m_diameter(44)
{
    // Repaint on hover to show the hover color.
    setAttribute(Qt::WA_Hover);
    setToolButtonStyle(Qt::ToolButtonIconOnly);
    setFocusPolicy(Qt::TabFocus);
    // The size comes from the diameter, not from the style (padding, etc.).
    setSizePolicy(QSizePolicy::Fixed, QSizePolicy::Fixed);
}

QSize TransportPlayButton::sizeHint() const
{
    return QSize(m_diameter, m_diameter);
}

QSize TransportPlayButton::minimumSizeHint() const
{
    return sizeHint();
}

void TransportPlayButton::setDiameter(int diameter)
{
    m_diameter = qMax(16, diameter);
    updateGeometry();
    update();
}

QColor TransportPlayButton::fillColor() const
{
    return m_fillColor.isValid() ? m_fillColor : palette().color(QPalette::Highlight);
}

void TransportPlayButton::setFillColor(const QColor &color)
{
    m_fillColor = color;
    update();
}

QColor TransportPlayButton::hoverColor() const
{
    return m_hoverColor.isValid() ? m_hoverColor : fillColor().lighter(112);
}

void TransportPlayButton::setHoverColor(const QColor &color)
{
    m_hoverColor = color;
    update();
}

QColor TransportPlayButton::pressedColor() const
{
    return m_pressedColor.isValid() ? m_pressedColor : fillColor().darker(112);
}

void TransportPlayButton::setPressedColor(const QColor &color)
{
    m_pressedColor = color;
    update();
}

QColor TransportPlayButton::glyphColor() const
{
    return m_glyphColor.isValid() ? m_glyphColor : palette().color(QPalette::HighlightedText);
}

void TransportPlayButton::setGlyphColor(const QColor &color)
{
    m_glyphColor = color;
    update();
}

QColor TransportPlayButton::disabledFillColor() const
{
    return m_disabledFillColor.isValid() ? m_disabledFillColor : palette().color(QPalette::Button);
}

void TransportPlayButton::setDisabledFillColor(const QColor &color)
{
    m_disabledFillColor = color;
    update();
}

QColor TransportPlayButton::disabledGlyphColor() const
{
    return m_disabledGlyphColor.isValid()
               ? m_disabledGlyphColor
               : palette().color(QPalette::Disabled, QPalette::ButtonText);
}

void TransportPlayButton::setDisabledGlyphColor(const QColor &color)
{
    m_disabledGlyphColor = color;
    update();
}

void TransportPlayButton::paintEvent(QPaintEvent *)
{
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing);

    const bool enabled = isEnabled();
    QColor fill = fillColor();
    if (!enabled)
        fill = disabledFillColor();
    else if (isDown())
        fill = pressedColor();
    else if (underMouse())
        fill = hoverColor();
    const QColor glyph = enabled ? glyphColor() : disabledGlyphColor();

    const qreal diameter = qMin(width(), height());
    const QRectF circle((width() - diameter) / 2.0, (height() - diameter) / 2.0, diameter, diameter);
    p.setPen(Qt::NoPen);
    p.setBrush(fill);
    p.drawEllipse(circle);

    if (hasFocus()) {
        QColor ring = glyph;
        ring.setAlphaF(0.6);
        p.setPen(QPen(ring, 2));
        p.setBrush(Qt::NoBrush);
        p.drawEllipse(circle.adjusted(3, 3, -3, -3));
    }

    // Paint the action's glyph (play, pause or stop) in the glyph color.
    QPixmap pixmap = icon().pixmap(iconSize(), devicePixelRatioF());
    if (!pixmap.isNull()) {
        QPainter tint(&pixmap);
        tint.setCompositionMode(QPainter::CompositionMode_SourceIn);
        tint.fillRect(pixmap.rect(), glyph);
        tint.end();
        const QSizeF size = pixmap.deviceIndependentSize();
        p.drawPixmap(QPointF(circle.center().x() - size.width() / 2.0,
                             circle.center().y() - size.height() / 2.0),
                     pixmap);
    }
}
