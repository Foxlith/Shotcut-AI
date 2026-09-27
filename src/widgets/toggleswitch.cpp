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

#include "toggleswitch.h"

#include <QPainter>

static const QSize kSwitchSize(32, 18);
static const int kKnobMargin = 2;

ToggleSwitch::ToggleSwitch(QWidget *parent)
    : QAbstractButton(parent)
    , m_offColor(0x2A, 0x2E, 0x37)
    , m_offHoverColor(0x34, 0x39, 0x44)
    , m_offPressedColor(0x26, 0x2A, 0x33)
    , m_knobColor(Qt::white)
    , m_disabledColor(0x1F, 0x22, 0x29)
    , m_disabledKnobColor(0x5F, 0x66, 0x72)
    , m_position(0.0)
{
    setCheckable(true);
    setCursor(Qt::PointingHandCursor);
    setFocusPolicy(Qt::TabFocus);
    setAttribute(Qt::WA_Hover);
    setSizePolicy(QSizePolicy::Fixed, QSizePolicy::Fixed);
    m_animation.setDuration(120);
    m_animation.setEasingCurve(QEasingCurve::OutCubic);
    connect(&m_animation, &QVariantAnimation::valueChanged, this, [this](const QVariant &value) {
        m_position = value.toReal();
        update();
    });
}

QSize ToggleSwitch::sizeHint() const
{
    return kSwitchSize;
}

QSize ToggleSwitch::minimumSizeHint() const
{
    return kSwitchSize;
}

QColor ToggleSwitch::onColor() const
{
    return m_onColor.isValid() ? m_onColor : palette().color(QPalette::Highlight);
}

void ToggleSwitch::setOnColor(const QColor &color)
{
    m_onColor = color;
    update();
}

void ToggleSwitch::setOffColor(const QColor &color)
{
    m_offColor = color;
    update();
}

void ToggleSwitch::setOffHoverColor(const QColor &color)
{
    m_offHoverColor = color;
    update();
}

void ToggleSwitch::setOffPressedColor(const QColor &color)
{
    m_offPressedColor = color;
    update();
}

void ToggleSwitch::setKnobColor(const QColor &color)
{
    m_knobColor = color;
    update();
}

void ToggleSwitch::setDisabledColor(const QColor &color)
{
    m_disabledColor = color;
    update();
}

void ToggleSwitch::setDisabledKnobColor(const QColor &color)
{
    m_disabledKnobColor = color;
    update();
}

void ToggleSwitch::checkStateSet()
{
    const qreal target = isChecked() ? 1.0 : 0.0;
    m_animation.stop();
    if (isVisible() && m_position != target) {
        m_animation.setStartValue(m_position);
        m_animation.setEndValue(target);
        m_animation.start();
    } else {
        m_position = target;
        update();
    }
}

void ToggleSwitch::paintEvent(QPaintEvent *)
{
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing);

    QRectF track(QPointF(0, 0), QSizeF(kSwitchSize));
    track.moveCenter(QRectF(rect()).center());
    const qreal radius = track.height() / 2.0;

    QColor trackColor;
    QColor knob = m_knobColor;
    if (!isEnabled()) {
        trackColor = m_disabledColor;
        knob = m_disabledKnobColor;
    } else if (isChecked()) {
        trackColor = onColor();
        if (isDown())
            trackColor = trackColor.darker(112);
        else if (underMouse())
            trackColor = trackColor.lighter(108);
    } else {
        trackColor = isDown() ? m_offPressedColor : (underMouse() ? m_offHoverColor : m_offColor);
    }
    p.setPen(Qt::NoPen);
    p.setBrush(trackColor);
    p.drawRoundedRect(track, radius, radius);

    if (hasFocus()) {
        p.setPen(QPen(onColor(), 2));
        p.setBrush(Qt::NoBrush);
        p.drawRoundedRect(track.adjusted(-1, -1, 1, 1), radius + 1, radius + 1);
    }

    const qreal diameter = track.height() - 2 * kKnobMargin;
    const qreal travel = track.width() - 2 * kKnobMargin - diameter;
    const QRectF knobRect(track.left() + kKnobMargin + travel * m_position,
                          track.top() + kKnobMargin,
                          diameter,
                          diameter);
    p.setPen(Qt::NoPen);
    p.setBrush(knob);
    p.drawEllipse(knobRect);
}
