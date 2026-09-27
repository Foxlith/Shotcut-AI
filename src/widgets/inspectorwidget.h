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

#ifndef INSPECTORWIDGET_H
#define INSPECTORWIDGET_H

#include <QFutureWatcher>
#include <QHash>
#include <QIcon>
#include <QImage>
#include <QPointer>
#include <QRectF>
#include <QScrollArea>
#include <QTimer>

class FilterController;
class QmlFilter;
class QmlMetadata;
class QFrame;
class QLabel;
class QPushButton;
class QSlider;
class QSpinBox;
class QVBoxLayout;
class ToggleSwitch;
namespace Mlt {
class Producer;
class Service;
} // namespace Mlt

/*!
  \class InspectorFilterRow
  \brief One attached filter in the Inspector: icon, name and an on/off switch.

  Click selects the filter (it becomes the current filter of the Filters
  panel), double-click or Enter opens it in the Filters panel and the switch
  (or Space) enables or disables it.
*/
class InspectorFilterRow : public QWidget
{
    Q_OBJECT
public:
    explicit InspectorFilterRow(QWidget *parent = nullptr);
    void setRow(int row) { m_row = row; }
    void setName(const QString &name);
    void setIcon(const QIcon &icon);
    void setEnabledFilter(bool enabled);
    void setToggleVisible(bool visible);
    void setCurrent(bool current);
    bool isCurrent() const { return m_current; }
    QSize sizeHint() const override;

signals:
    void clicked(int row);
    void activated(int row);
    void toggled(int row);

protected:
    void paintEvent(QPaintEvent *event) override;
    void resizeEvent(QResizeEvent *event) override;
    void mousePressEvent(QMouseEvent *event) override;
    void mouseReleaseEvent(QMouseEvent *event) override;
    void mouseDoubleClickEvent(QMouseEvent *event) override;
    void keyPressEvent(QKeyEvent *event) override;

private:
    int m_row{-1};
    QString m_name;
    QIcon m_icon;
    bool m_filterEnabled{true};
    bool m_current{false};
    bool m_pressed{false};
    ToggleSwitch *m_switch;
};

/*!
  \class InspectorWidget
  \brief The content of the Inspector panel (formerly Properties).

  From top to bottom: the header of the selected item (thumbnail, name and
  technical metadata), the TRANSFORM section (position, scale, rotation and
  opacity of a clip), the FILTERS section (the attached filters with on/off
  switches and "+ Add filter") and the properties widget of the clip, track
  or output that Properties showed before.

  TRANSFORM edits the "Size, Position & Rotate" and "Opacity" filters through
  the FilterController, so the changes are undoable and the Filters panel
  shows the same values. When the clip does not have the filter yet, the
  first change adds it.
*/
class InspectorWidget : public QScrollArea
{
    Q_OBJECT
public:
    explicit InspectorWidget(QWidget *parent = nullptr);
    void setFilterController(FilterController *controller);

    /// The widget that the Properties panel showed for the current producer.
    QWidget *producerWidget() const { return m_producerWidget; }
    /// Shows \a widget below the Inspector sections and deletes the previous one
    /// (like QScrollArea::setWidget()); nullptr removes it.
    void setProducerWidget(QWidget *widget);

signals:
    /// The user asked to edit a filter in the Filters panel.
    void filtersPanelRequested();

public slots:
    /// Schedules an update of every section (coalesced).
    void refresh();

protected:
    void resizeEvent(QResizeEvent *event) override;
    bool viewportEvent(QEvent *event) override;

private:
    void doRefresh();
    void updateSectionWidths();
    void updateHeader(Mlt::Producer *producer);
    void updateTransform(Mlt::Producer *producer);
    void updateFilters();
    void updateTitleElision();
    int findFilter(const QString &id) const;
    QRectF defaultRect() const;
    QmlFilter *beginEdit(const QString &id, const QString &description);
    void setFilterDefaults(const QString &id, Mlt::Service &service);
    void applyGeometry(const QString &description);
    void applyRotation(int degrees);
    void applyOpacity(int percent);
    QIcon filterIcon(QmlMetadata *meta);
    QLabel *createSectionLabel(const QString &text, const char *name);
    QFrame *createDivider();

    FilterController *m_controller{nullptr};
    QPointer<QWidget> m_producerWidget;
    QTimer m_refreshTimer;
    bool m_updating{false};

    QWidget *m_content;
    QLabel *m_emptyLabel;
    QWidget *m_header;
    QLabel *m_thumbnail;
    QLabel *m_title;
    QLabel *m_meta;
    QString m_titleText;
    QString m_thumbnailKey;
    QFutureWatcher<QImage> m_thumbnailWatcher;

    QWidget *m_transform;
    QSpinBox *m_positionX;
    QSpinBox *m_positionY;
    QSlider *m_scaleSlider;
    QSpinBox *m_scaleValue;
    QSlider *m_rotationSlider;
    QSpinBox *m_rotationValue;
    QSlider *m_opacitySlider;
    QSpinBox *m_opacityValue;
    QLabel *m_transformHint;
    double m_aspectRatio{16.0 / 9.0};

    QWidget *m_filters;
    QLabel *m_filtersLabel;
    QVBoxLayout *m_filterRowsLayout;
    QList<InspectorFilterRow *> m_filterRows;
    QPushButton *m_addFilterButton;
    QHash<QmlMetadata *, QIcon> m_icons;

    QWidget *m_properties;
    QVBoxLayout *m_producerLayout;
};

#endif // INSPECTORWIDGET_H
