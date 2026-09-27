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

#ifndef TOGGLESWITCH_H
#define TOGGLESWITCH_H

#include <QAbstractButton>
#include <QColor>
#include <QVariantAnimation>

/*!
  \class ToggleSwitch
  \brief A checkable on/off switch (32 x 18 px pill with a round knob).

  The track is painted in onColor when checked (the palette Highlight by
  default, so it follows the accent color) and in offColor otherwise. All the
  colors can be themed from a style sheet with qproperty-onColor, and so on.
*/
class ToggleSwitch : public QAbstractButton
{
    Q_OBJECT
    Q_PROPERTY(QColor onColor READ onColor WRITE setOnColor)
    Q_PROPERTY(QColor offColor READ offColor WRITE setOffColor)
    Q_PROPERTY(QColor offHoverColor READ offHoverColor WRITE setOffHoverColor)
    Q_PROPERTY(QColor offPressedColor READ offPressedColor WRITE setOffPressedColor)
    Q_PROPERTY(QColor knobColor READ knobColor WRITE setKnobColor)
    Q_PROPERTY(QColor disabledColor READ disabledColor WRITE setDisabledColor)
    Q_PROPERTY(QColor disabledKnobColor READ disabledKnobColor WRITE setDisabledKnobColor)

public:
    explicit ToggleSwitch(QWidget *parent = nullptr);
    QSize sizeHint() const override;
    QSize minimumSizeHint() const override;

    QColor onColor() const;
    void setOnColor(const QColor &color);
    QColor offColor() const { return m_offColor; }
    void setOffColor(const QColor &color);
    QColor offHoverColor() const { return m_offHoverColor; }
    void setOffHoverColor(const QColor &color);
    QColor offPressedColor() const { return m_offPressedColor; }
    void setOffPressedColor(const QColor &color);
    QColor knobColor() const { return m_knobColor; }
    void setKnobColor(const QColor &color);
    QColor disabledColor() const { return m_disabledColor; }
    void setDisabledColor(const QColor &color);
    QColor disabledKnobColor() const { return m_disabledKnobColor; }
    void setDisabledKnobColor(const QColor &color);

protected:
    void paintEvent(QPaintEvent *event) override;
    void checkStateSet() override;

private:
    QColor m_onColor;
    QColor m_offColor;
    QColor m_offHoverColor;
    QColor m_offPressedColor;
    QColor m_knobColor;
    QColor m_disabledColor;
    QColor m_disabledKnobColor;
    qreal m_position; // 0 = off, 1 = on
    QVariantAnimation m_animation;
};

#endif // TOGGLESWITCH_H
