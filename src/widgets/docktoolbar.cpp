/*
 * Copyright (c) 2022-2025 Meltytech, LLC
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your tbOption) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "docktoolbar.h"

#include "settings.h"

#include <QEvent>
#include <QPainter>
#include <QStyle>
#include <QStyleOptionToolBar>

DockToolBar::DockToolBar(const QString &title, QWidget *parent)
    : QToolBar(title, parent)
    , m_area(Qt::TopToolBarArea)
{
    setMovable(false);
    setToolButtonStyle(Qt::ToolButtonIconOnly);
    setFloatable(false);
    setProperty("Movable", QVariant(false));
    updateStyle();
    connect(&Settings, SIGNAL(smallIconsChanged()), SLOT(updateStyle()));
}

void DockToolBar::setAreaHint(Qt::ToolBarArea area)
{
    m_area = area;
}

void DockToolBar::paintEvent(QPaintEvent *event)
{
    if (isGrafitoTimeline()) {
        // Flat Grafito bar painted by the style sheet (DockToolBar#timelineToolbar).
        QToolBar::paintEvent(event);
        return;
    }
    QPainter p(this);
    QLinearGradient gradient
        = QLinearGradient(rect().left(), rect().center().y(), rect().right(), rect().center().y());
    gradient.setColorAt(0, palette().window().color().lighter(104));
    gradient.setColorAt(1, palette().window().color());
    p.fillRect(rect(), gradient);
    if (m_area == Qt::TopToolBarArea) {
        // Apply the same styling that is applied to main window toolbars.
        // This creates extra lines of separation between the toolbar and the
        // dock contents.
        QColor light = QColor(255, 255, 255, 90);
        QColor shadow = QColor(0, 0, 0, 60);
        p.setPen(shadow);
        p.drawLine(rect().bottomLeft(), rect().bottomRight());
        p.setPen(light);
        p.drawLine(rect().topLeft(), rect().topRight());
    }
}

bool DockToolBar::event(QEvent *event)
{
    if (event->type() == QEvent::DynamicPropertyChange) {
        updateStyle();
    }
    return QToolBar::event(event);
}

bool DockToolBar::isGrafitoTimeline() const
{
    return objectName() == "timelineToolbar"
           && palette().color(QPalette::Window).lightnessF() < 0.5;
}

void DockToolBar::updateStyle()
{
    bool isTimeline = (objectName() == "timelineToolbar") || property("compact").toBool();
    int iconDim = isTimeline ? 15 : (Settings.smallIcons() ? 15 : 18);
    int barHeight = isTimeline ? 26 : (Settings.smallIcons() ? 26 : 30);
    // Grafito timeline toolbar: 44 px with 15 px icons in groups (plan.md 3.3).
    if (isGrafitoTimeline())
        barHeight = 44;
    setFixedHeight(barHeight);
    setIconSize(QSize(iconDim, iconDim));
    QString styleSheet = QString::fromUtf8("   \
         QToolButton {                          \
           width:%1px;                          \
           height:%1px;                         \
           color:#9AA1AD;                       \
         }                                      \
         QToolButton:hover {                    \
           color:#E8EAEE;                       \
           background-color:#262A33;            \
         }                                      \
         QToolButton:pressed {                  \
           background-color:#FF7A45;            \
           color:#140A05;                       \
           border:1px solid #FF7A45;            \
         }                                      \
         QToolButton[popupMode=\"1\"] {         \
           padding-right: 12px;                 \
         }                                      \
         QToolButton:checked,                   \
         QToolButton[active=\"true\"] {         \
           color:#FF7A45;                       \
           background-color:rgba(255, 122, 69, 0.18); \
           border:1px solid #FF7A45;            \
         }                                      \
         QToolButton:checked:hover,             \
         QToolButton[active=\"true\"]:hover {   \
           background-color:rgba(255, 122, 69, 0.28); \
           color:#FF7A45;                       \
           border:1px solid #FF7A45;            \
         }                                      \
         QToolButton:checked:pressed,           \
         QToolButton[active=\"true\"]:pressed { \
           background-color:#FF7A45;            \
           color:#140A05;                       \
           border:1px solid #FF7A45;            \
         }                                      \
         QToolButton:disabled {                 \
           color:#5F6672;                       \
         }                                      \
         QToolBar {                             \
           spacing:%2px;                        \
           padding:%3;                          \
         }                                      \
        ")
                             .arg(iconDim + 6)
                             .arg(isGrafitoTimeline() ? 4 : 3)
                             .arg(isGrafitoTimeline() ? QStringLiteral("0px 8px")
                                                      : QStringLiteral("1px"));
    setStyleSheet(styleSheet);
}
