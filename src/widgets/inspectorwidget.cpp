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

#include "inspectorwidget.h"

#include "actions.h"
#include "controllers/filtercontroller.h"
#include "mltcontroller.h"
#include "models/attachedfiltersmodel.h"
#include "qmltypes/qmlfilter.h"
#include "qmltypes/qmlmetadata.h"
#include "qmltypes/thumbnailprovider.h"
#include "shotcut_mlt_properties.h"
#include "util.h"
#include "widgets/toggleswitch.h"

#include <QAction>
#include <QFrame>
#include <QGridLayout>
#include <QHBoxLayout>
#include <QKeyEvent>
#include <QLabel>
#include <QMouseEvent>
#include <QPainter>
#include <QPainterPath>
#include <QPushButton>
#include <QSlider>
#include <QSpinBox>
#include <QUrl>
#include <QVBoxLayout>
#include <QtConcurrent/QtConcurrentRun>

#include <cmath>
#include <memory>

// Filters edited by the TRANSFORM section (see src/qml/filters/size_position and opacity).
static const QString kSizePositionId = QStringLiteral("affineSizePosition");
static const QString kOpacityId = QStringLiteral("brightnessOpacity");
static const char *kRectProperty = "transition.rect";
static const char *kRotationProperty = "transition.fix_rotate_x";
// State kept by the Size, Position & Rotate filter user interface (SizePositionUI.qml).
static const char *kMiddleValue = "_shotcut:middleValue";
static const char *kRotationMiddleValue = "_shotcut:rotationMiddleValue";

static const QSize kThumbnailSize(64, 36);
static const int kFilterRowHeight = 36;
static const QColor kSurface(0x1D, 0x20, 0x27);
static const QColor kSurfaceHover(0x26, 0x2A, 0x33);
static const QColor kSurfacePressed(0x1F, 0x22, 0x29);
static const QColor kBorder(0x22, 0x25, 0x2D);
static const QColor kThumbBackground(0x0F, 0x11, 0x15);
static const QColor kText(0xE8, 0xEA, 0xEE);
static const QColor kMutedText(0x9A, 0xA1, 0xAD);
static const QColor kDisabledText(0x5F, 0x66, 0x72);
static const QColor kWaveform(0x3D, 0xD6, 0xB0, 217);

// "mm:ss" (or "h:mm:ss") for the header metadata.
static QString shortDuration(int frames)
{
    const double fps = MLT.profile().fps();
    const int seconds = fps > 0 ? int(frames / fps) : 0;
    const int hours = seconds / 3600;
    const QString minutesSeconds = QStringLiteral("%1:%2")
                                       .arg((seconds / 60) % 60, 2, 10, QLatin1Char('0'))
                                       .arg(seconds % 60, 2, 10, QLatin1Char('0'));
    return hours ? QStringLiteral("%1:%2").arg(hours).arg(minutesSeconds) : minutesSeconds;
}

// Keyframes use "frame=value" pairs; a static value never contains '='.
static bool isKeyframed(Mlt::Service &service, const char *name)
{
    return QString::fromUtf8(service.get(name)).contains('=');
}

static bool hasSimpleKeyframes(Mlt::Service &service)
{
    return service.time_to_frames(service.get(kShotcutAnimInProperty)) > 0
           || service.time_to_frames(service.get(kShotcutAnimOutProperty)) > 0;
}

// Same as QmlFilter::getRect(): percentages are relative to the video mode.
static QRectF serviceRect(Mlt::Service &service, const char *name)
{
    const char *s = service.get(name);
    if (!s)
        return QRectF();
    const mlt_rect rect = service.get_rect(name);
    if (::strchr(s, '%')) {
        return QRectF(rect.x * MLT.profile().width(),
                      rect.y * MLT.profile().height(),
                      rect.w * MLT.profile().width(),
                      rect.h * MLT.profile().height());
    }
    return QRectF(rect.x, rect.y, rect.w, rect.h);
}

static bool isAudioOnly(Mlt::Producer &producer)
{
    const QString service = QString::fromLatin1(producer.get("mlt_service"));
    const QString resource = QString::fromUtf8(producer.get("resource"));
    if (service.startsWith("avformat"))
        return producer.get_int("video_index") < 0 && producer.get_int("audio_index") >= 0;
    return service == "tone" || resource.startsWith("pulse:") || resource.startsWith("alsa:")
           || resource.startsWith("jack:");
}

// The TRANSFORM section applies to video, image and generator clips.
static bool isVisualClip(Mlt::Producer *producer)
{
    if (!producer || !producer->is_valid() || producer->is_blank())
        return false;
    if (producer->type() == mlt_service_playlist_type
        || producer->type() == mlt_service_tractor_type)
        return false;
    if (producer->get(kShotcutTransitionProperty)
        || producer->parent().get(kShotcutTransitionProperty))
        return false;
    return !isAudioOnly(*producer);
}

static void paintPlaceholder(QPainter &painter, const QRectF &rect, bool audio)
{
    painter.save();
    painter.setRenderHint(QPainter::Antialiasing);
    if (audio) {
        static const qreal levels[] = {0.4, 0.75, 1.0, 0.55, 0.85, 0.45, 0.7, 0.35};
        const int bars = int(sizeof(levels) / sizeof(levels[0]));
        const qreal step = 5.0;
        const qreal x0 = rect.center().x() - (bars * step - 2.0) / 2.0;
        painter.setPen(Qt::NoPen);
        painter.setBrush(kWaveform);
        for (int i = 0; i < bars; i++) {
            const qreal h = rect.height() * 0.55 * levels[i];
            painter.drawRoundedRect(QRectF(x0 + i * step, rect.center().y() - h / 2, 3, h),
                                    1.5,
                                    1.5);
        }
    } else {
        const QRectF glyph(rect.center() - QPointF(10, 7), QSizeF(20, 14));
        painter.setPen(QPen(kDisabledText, 1.5));
        painter.setBrush(Qt::NoBrush);
        painter.drawRoundedRect(glyph, 3, 3);
        QPolygonF triangle;
        triangle << glyph.center() + QPointF(-2.5, -3.5) << glyph.center() + QPointF(4, 0)
                 << glyph.center() + QPointF(-2.5, 3.5);
        painter.setBrush(kDisabledText);
        painter.drawPolygon(triangle);
    }
    painter.restore();
}

static QPixmap thumbnailPixmap(const QImage &image, bool audio, qreal devicePixelRatio)
{
    QPixmap pixmap(kThumbnailSize * devicePixelRatio);
    pixmap.setDevicePixelRatio(devicePixelRatio);
    pixmap.fill(Qt::transparent);
    QPainter painter(&pixmap);
    painter.setRenderHints(QPainter::Antialiasing | QPainter::SmoothPixmapTransform);
    const QRectF rect(QPointF(0, 0), QSizeF(kThumbnailSize));
    QPainterPath path;
    path.addRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 6, 6);
    painter.save();
    painter.setClipPath(path);
    painter.fillRect(rect, kThumbBackground);
    if (!audio && image.width() > 1 && image.height() > 1) {
        QRectF target(QPointF(),
                      QSizeF(image.size()).scaled(rect.size(), Qt::KeepAspectRatioByExpanding));
        target.moveCenter(rect.center());
        painter.drawImage(target, image);
    } else {
        paintPlaceholder(painter, rect, audio);
    }
    painter.restore();
    painter.setPen(QPen(kBorder, 1));
    painter.setBrush(Qt::NoBrush);
    painter.drawPath(path);
    return pixmap;
}

// ---------------------------------------------------------------------------
// InspectorFilterRow
// ---------------------------------------------------------------------------

InspectorFilterRow::InspectorFilterRow(QWidget *parent)
    : QWidget(parent)
    , m_switch(new ToggleSwitch(this))
{
    setObjectName("inspectorFilterRow");
    setAttribute(Qt::WA_Hover);
    setFocusPolicy(Qt::TabFocus);
    setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
    m_switch->setObjectName("inspectorFilterSwitch");
    m_switch->resize(m_switch->sizeHint());
    m_switch->setToolTip(tr("Enable or disable the filter"));
    connect(m_switch, &QAbstractButton::clicked, this, [this]() { emit toggled(m_row); });
}

QSize InspectorFilterRow::sizeHint() const
{
    return QSize(200, kFilterRowHeight);
}

void InspectorFilterRow::setName(const QString &name)
{
    if (name != m_name) {
        m_name = name;
        update();
    }
}

void InspectorFilterRow::setIcon(const QIcon &icon)
{
    m_icon = icon;
    update();
}

void InspectorFilterRow::setEnabledFilter(bool enabled)
{
    m_filterEnabled = enabled;
    if (m_switch->isChecked() != enabled) {
        QSignalBlocker blocker(m_switch);
        m_switch->setChecked(enabled);
    }
    update();
}

void InspectorFilterRow::setToggleVisible(bool visible)
{
    m_switch->setVisible(visible);
    update();
}

void InspectorFilterRow::setCurrent(bool current)
{
    if (current != m_current) {
        m_current = current;
        update();
    }
}

void InspectorFilterRow::resizeEvent(QResizeEvent *event)
{
    QWidget::resizeEvent(event);
    m_switch->move(width() - 10 - m_switch->width(), (height() - m_switch->height()) / 2);
}

void InspectorFilterRow::paintEvent(QPaintEvent *)
{
    QPainter p(this);
    p.setRenderHints(QPainter::Antialiasing | QPainter::SmoothPixmapTransform);
    const QColor accent = palette().color(QPalette::Highlight);
    const QRectF bounds = QRectF(rect()).adjusted(0.5, 0.5, -0.5, -0.5);
    QPainterPath shape;
    shape.addRoundedRect(bounds, 6, 6);

    // Row: #1D2027 surface, #262A33 on hover, #1F2229 pressed, 6 px radius. Light
    // themes take the colors from the palette.
    const bool dark = palette().color(QPalette::Window).lightnessF() < 0.5;
    QColor surface = dark ? kSurface : palette().color(QPalette::AlternateBase);
    if (m_pressed)
        surface = dark ? kSurfacePressed : palette().color(QPalette::Mid);
    else if (underMouse())
        surface = dark ? kSurfaceHover : palette().color(QPalette::Midlight);
    p.fillPath(shape, surface);
    if (m_current) {
        // The current filter (the one shown in the Filters panel): 2 px accent border on the left.
        p.save();
        p.setClipPath(shape);
        p.fillRect(QRectF(0, 0, 2, height()), accent);
        p.restore();
    }
    if (hasFocus()) {
        p.setPen(QPen(accent, 2));
        p.drawRoundedRect(QRectF(rect()).adjusted(1, 1, -1, -1), 6, 6);
    }

    const QRect iconRect(12, (height() - 18) / 2, 18, 18);
    QPainterPath iconShape;
    iconShape.addRoundedRect(iconRect, 4, 4);
    p.save();
    p.setClipPath(iconShape);
    p.setOpacity(m_filterEnabled ? 1.0 : 0.45);
    m_icon.paint(&p, iconRect);
    p.restore();

    QFont nameFont = font();
    nameFont.setPixelSize(12);
    nameFont.setWeight(QFont::Medium);
    p.setFont(nameFont);
    const QColor text = dark ? kText : palette().color(QPalette::Text);
    const QColor muted = dark ? kMutedText : palette().color(QPalette::PlaceholderText);
    p.setPen(!isEnabled() ? kDisabledText : (m_filterEnabled ? text : muted));
    const int left = iconRect.right() + 11;
    const int right = m_switch->isVisible() ? m_switch->x() - 8 : width() - 10;
    const QRect textRect(left, 0, qMax(0, right - left), height());
    p.drawText(textRect,
               Qt::AlignLeft | Qt::AlignVCenter,
               QFontMetrics(nameFont).elidedText(m_name, Qt::ElideRight, textRect.width()));
}

void InspectorFilterRow::mousePressEvent(QMouseEvent *event)
{
    if (event->button() == Qt::LeftButton) {
        m_pressed = true;
        update();
        event->accept();
        return;
    }
    QWidget::mousePressEvent(event);
}

void InspectorFilterRow::mouseReleaseEvent(QMouseEvent *event)
{
    if (event->button() == Qt::LeftButton && m_pressed) {
        m_pressed = false;
        update();
        if (rect().contains(event->position().toPoint()))
            emit clicked(m_row);
        event->accept();
        return;
    }
    QWidget::mouseReleaseEvent(event);
}

void InspectorFilterRow::mouseDoubleClickEvent(QMouseEvent *event)
{
    if (event->button() == Qt::LeftButton) {
        emit activated(m_row);
        event->accept();
        return;
    }
    QWidget::mouseDoubleClickEvent(event);
}

void InspectorFilterRow::keyPressEvent(QKeyEvent *event)
{
    switch (event->key()) {
    case Qt::Key_Return:
    case Qt::Key_Enter:
        emit activated(m_row);
        break;
    case Qt::Key_Space:
        if (m_switch->isVisible())
            m_switch->click();
        else
            emit clicked(m_row);
        break;
    default:
        QWidget::keyPressEvent(event);
        return;
    }
    event->accept();
}

// ---------------------------------------------------------------------------
// InspectorWidget
// ---------------------------------------------------------------------------

static QSpinBox *createNumberField(const char *name, int minimum, int maximum, const QString &suffix)
{
    auto spinBox = new QSpinBox;
    spinBox->setObjectName(name);
    spinBox->setRange(minimum, maximum);
    spinBox->setSuffix(suffix);
    spinBox->setButtonSymbols(QAbstractSpinBox::NoButtons);
    spinBox->setAlignment(Qt::AlignRight | Qt::AlignVCenter);
    // Apply on Enter, focus out or the arrow keys, not on every typed digit.
    spinBox->setKeyboardTracking(false);
    spinBox->setAccelerated(true);
    return spinBox;
}

static QSlider *createSlider(const char *name, int minimum, int maximum)
{
    auto slider = new QSlider(Qt::Horizontal);
    slider->setObjectName(name);
    slider->setRange(minimum, maximum);
    slider->setCursor(Qt::PointingHandCursor);
    return slider;
}

static QLabel *createRowLabel(const QString &text)
{
    auto label = new QLabel(text);
    label->setObjectName("inspectorRowLabel");
    label->setMinimumWidth(62);
    return label;
}

InspectorWidget::InspectorWidget(QWidget *parent)
    : QScrollArea(parent)
{
    setObjectName("inspector");
    setWidgetResizable(true);
    setFrameShape(QFrame::NoFrame);
    m_refreshTimer.setSingleShot(true);
    m_refreshTimer.setInterval(0);
    connect(&m_refreshTimer, &QTimer::timeout, this, &InspectorWidget::doRefresh);

    m_content = new QWidget;
    m_content->setObjectName("inspectorContent");
    auto layout = new QVBoxLayout(m_content);
    layout->setContentsMargins(12, 12, 12, 12);
    layout->setSpacing(12);

    m_emptyLabel = new QLabel(tr("Select a clip in the timeline or the playlist to inspect it."));
    m_emptyLabel->setObjectName("inspectorEmpty");
    m_emptyLabel->setAlignment(Qt::AlignCenter);
    m_emptyLabel->setWordWrap(true);
    layout->addWidget(m_emptyLabel, 0, Qt::AlignLeft);

    // Header of the selected item: thumbnail, name and technical metadata.
    m_header = new QWidget;
    m_header->setObjectName("inspectorHeader");
    auto headerLayout = new QHBoxLayout(m_header);
    headerLayout->setContentsMargins(0, 0, 0, 0);
    headerLayout->setSpacing(10);
    m_thumbnail = new QLabel;
    m_thumbnail->setObjectName("inspectorThumbnail");
    m_thumbnail->setFixedSize(kThumbnailSize);
    headerLayout->addWidget(m_thumbnail);
    auto titles = new QVBoxLayout;
    titles->setSpacing(2);
    m_title = new QLabel;
    m_title->setObjectName("inspectorTitle");
    m_title->setSizePolicy(QSizePolicy::Ignored, QSizePolicy::Preferred);
    m_meta = new QLabel;
    m_meta->setObjectName("inspectorMeta");
    m_meta->setSizePolicy(QSizePolicy::Ignored, QSizePolicy::Preferred);
    titles->addWidget(m_title);
    titles->addWidget(m_meta);
    headerLayout->addLayout(titles, 1);
    layout->addWidget(m_header, 0, Qt::AlignLeft);

    // TRANSFORM: position, scale, rotation and opacity.
    m_transform = new QWidget;
    m_transform->setObjectName("inspectorTransform");
    auto transformLayout = new QVBoxLayout(m_transform);
    transformLayout->setContentsMargins(0, 0, 0, 0);
    transformLayout->setSpacing(10);
    transformLayout->addWidget(createDivider());
    transformLayout->addWidget(createSectionLabel(tr("Transform"), "inspectorTransformLabel"));
    auto grid = new QGridLayout;
    grid->setContentsMargins(0, 0, 0, 0);
    grid->setHorizontalSpacing(8);
    grid->setVerticalSpacing(8);
    grid->addWidget(createRowLabel(tr("Position")), 0, 0);
    auto position = new QHBoxLayout;
    position->setSpacing(6);
    auto xLabel = new QLabel(QStringLiteral("X"));
    xLabel->setObjectName("inspectorAxisLabel");
    m_positionX = createNumberField("inspectorPositionX", -99999, 99999, QString());
    m_positionX->setToolTip(tr("Horizontal offset from the center in pixels"));
    auto yLabel = new QLabel(QStringLiteral("Y"));
    yLabel->setObjectName("inspectorAxisLabel");
    m_positionY = createNumberField("inspectorPositionY", -99999, 99999, QString());
    m_positionY->setToolTip(tr("Vertical offset from the center in pixels"));
    position->addWidget(xLabel);
    position->addWidget(m_positionX, 1);
    position->addWidget(yLabel);
    position->addWidget(m_positionY, 1);
    grid->addLayout(position, 0, 1, 1, 2);

    grid->addWidget(createRowLabel(tr("Scale")), 1, 0);
    m_scaleSlider = createSlider("inspectorScaleSlider", 1, 400);
    m_scaleValue = createNumberField("inspectorScaleValue", 1, 1000, QStringLiteral("%"));
    grid->addWidget(m_scaleSlider, 1, 1);
    grid->addWidget(m_scaleValue, 1, 2);

    grid->addWidget(createRowLabel(tr("Rotation")), 2, 0);
    m_rotationSlider = createSlider("inspectorRotationSlider", -180, 180);
    m_rotationValue
        = createNumberField("inspectorRotationValue", -360, 360, QString::fromUtf8("\xC2\xB0"));
    grid->addWidget(m_rotationSlider, 2, 1);
    grid->addWidget(m_rotationValue, 2, 2);

    grid->addWidget(createRowLabel(tr("Opacity")), 3, 0);
    m_opacitySlider = createSlider("inspectorOpacitySlider", 0, 100);
    m_opacityValue = createNumberField("inspectorOpacityValue", 0, 100, QStringLiteral("%"));
    grid->addWidget(m_opacitySlider, 3, 1);
    grid->addWidget(m_opacityValue, 3, 2);
    for (auto spinBox : {m_scaleValue, m_rotationValue, m_opacityValue})
        spinBox->setFixedWidth(64);
    grid->setColumnStretch(1, 1);
    transformLayout->addLayout(grid);
    m_transformHint = new QLabel(tr("Keyframed values are edited in the Filters panel."));
    m_transformHint->setObjectName("inspectorTransformHint");
    m_transformHint->setWordWrap(true);
    m_transformHint->hide();
    transformLayout->addWidget(m_transformHint);
    layout->addWidget(m_transform, 0, Qt::AlignLeft);

    // FILTERS: attached filters with on/off switches and "+ Add filter".
    m_filters = new QWidget;
    m_filters->setObjectName("inspectorFilters");
    auto filtersLayout = new QVBoxLayout(m_filters);
    filtersLayout->setContentsMargins(0, 0, 0, 0);
    filtersLayout->setSpacing(8);
    filtersLayout->addWidget(createDivider());
    m_filtersLabel = createSectionLabel(tr("Filters"), "inspectorFiltersLabel");
    filtersLayout->addWidget(m_filtersLabel);
    m_filterRowsLayout = new QVBoxLayout;
    m_filterRowsLayout->setContentsMargins(0, 0, 0, 0);
    m_filterRowsLayout->setSpacing(4);
    filtersLayout->addLayout(m_filterRowsLayout);
    m_addFilterButton = new QPushButton(tr("Add filter"));
    m_addFilterButton->setObjectName("inspectorAddFilterButton");
    m_addFilterButton->setIcon(
        QIcon::fromTheme("list-add", QIcon(":/icons/oxygen/32x32/actions/list-add.png")));
    m_addFilterButton->setToolTip(tr("Choose a filter to add"));
    m_addFilterButton->setCursor(Qt::PointingHandCursor);
    m_addFilterButton->setAutoDefault(false);
    filtersLayout->addWidget(m_addFilterButton);
    layout->addWidget(m_filters, 0, Qt::AlignLeft);

    // The clip, track or output properties that the Properties panel showed.
    m_properties = new QWidget;
    m_properties->setObjectName("inspectorProperties");
    auto propertiesLayout = new QVBoxLayout(m_properties);
    propertiesLayout->setContentsMargins(0, 0, 0, 0);
    propertiesLayout->setSpacing(8);
    propertiesLayout->addWidget(createDivider());
    propertiesLayout->addWidget(createSectionLabel(tr("Properties"), "inspectorPropertiesLabel"));
    m_producerLayout = new QVBoxLayout;
    m_producerLayout->setContentsMargins(0, 0, 0, 0);
    propertiesLayout->addLayout(m_producerLayout);
    layout->addWidget(m_properties);
    layout->addStretch(1);

    setWidget(m_content);
    // Let the panel color show through (QScrollArea::setWidget() turns this on).
    m_content->setAutoFillBackground(false);
    viewport()->setAutoFillBackground(false);

    // Keep each slider and its numeric field in sync and apply the change.
    connect(m_scaleSlider, &QSlider::valueChanged, this, [this](int value) {
        if (m_updating)
            return;
        QSignalBlocker blocker(m_scaleValue);
        m_scaleValue->setValue(value);
        applyGeometry(tr("Scale"));
    });
    connect(m_scaleValue, qOverload<int>(&QSpinBox::valueChanged), this, [this](int value) {
        if (m_updating)
            return;
        QSignalBlocker blocker(m_scaleSlider);
        m_scaleSlider->setValue(value);
        applyGeometry(tr("Scale"));
    });
    connect(m_rotationSlider, &QSlider::valueChanged, this, [this](int value) {
        if (m_updating)
            return;
        QSignalBlocker blocker(m_rotationValue);
        m_rotationValue->setValue(value);
        applyRotation(value);
    });
    connect(m_rotationValue, qOverload<int>(&QSpinBox::valueChanged), this, [this](int value) {
        if (m_updating)
            return;
        QSignalBlocker blocker(m_rotationSlider);
        m_rotationSlider->setValue(value);
        applyRotation(value);
    });
    connect(m_opacitySlider, &QSlider::valueChanged, this, [this](int value) {
        if (m_updating)
            return;
        QSignalBlocker blocker(m_opacityValue);
        m_opacityValue->setValue(value);
        applyOpacity(value);
    });
    connect(m_opacityValue, qOverload<int>(&QSpinBox::valueChanged), this, [this](int value) {
        if (m_updating)
            return;
        QSignalBlocker blocker(m_opacitySlider);
        m_opacitySlider->setValue(value);
        applyOpacity(value);
    });
    for (auto spinBox : {m_positionX, m_positionY}) {
        connect(spinBox, qOverload<int>(&QSpinBox::valueChanged), this, [this]() {
            if (!m_updating)
                applyGeometry(tr("Position"));
        });
    }
    connect(m_addFilterButton, &QPushButton::clicked, this, []() {
        // Same as the Filters panel "+" button: shows the panel and its filter menu.
        if (QAction *action = Actions["filtersAddFilterAction"])
            action->trigger();
    });
    connect(&m_thumbnailWatcher, &QFutureWatcher<QImage>::finished, this, [this]() {
        if (m_thumbnailWatcher.property("key").toString() == m_thumbnailKey)
            m_thumbnail->setPixmap(
                thumbnailPixmap(m_thumbnailWatcher.result(), false, devicePixelRatioF()));
    });
    doRefresh();
}

void InspectorWidget::setFilterController(FilterController *controller)
{
    m_controller = controller;
    AttachedFiltersModel *model = controller->attachedModel();
    connect(model, &QAbstractItemModel::modelReset, this, &InspectorWidget::refresh);
    connect(model, &QAbstractItemModel::rowsInserted, this, &InspectorWidget::refresh);
    connect(model, &QAbstractItemModel::rowsRemoved, this, &InspectorWidget::refresh);
    connect(model, &QAbstractItemModel::rowsMoved, this, &InspectorWidget::refresh);
    connect(model, &QAbstractItemModel::dataChanged, this, &InspectorWidget::refresh);
    connect(model, &AttachedFiltersModel::trackTitleChanged, this, &InspectorWidget::refresh);
    connect(model,
            &AttachedFiltersModel::isProducerSelectedChanged,
            this,
            &InspectorWidget::refresh);
    // Reactivity: the selection, the current filter and its parameters.
    connect(controller, &FilterController::currentFilterChanged, this, &InspectorWidget::refresh);
    connect(controller, &FilterController::filterChanged, this, &InspectorWidget::refresh);
    connect(controller, &FilterController::undoOrRedo, this, &InspectorWidget::refresh);
    refresh();
}

void InspectorWidget::setProducerWidget(QWidget *widget)
{
    if (widget == m_producerWidget)
        return;
    delete m_producerWidget.data();
    m_producerWidget = widget;
    if (widget) {
        m_producerLayout->addWidget(widget);
        widget->show();
        // MainWindow may also delete it later (deleteLater()).
        connect(widget, &QObject::destroyed, this, &InspectorWidget::refresh);
    }
    refresh();
}

void InspectorWidget::refresh()
{
    m_refreshTimer.start();
}

void InspectorWidget::resizeEvent(QResizeEvent *event)
{
    QScrollArea::resizeEvent(event);
    updateTitleElision();
}

bool InspectorWidget::viewportEvent(QEvent *event)
{
    if (event->type() == QEvent::Resize)
        updateSectionWidths();
    return QScrollArea::viewportEvent(event);
}

void InspectorWidget::updateSectionWidths()
{
    // The properties widget may be wider than the panel (it scrolls horizontally
    // as before); keep the Inspector sections as wide as the visible area.
    const QMargins margins = m_content->layout()->contentsMargins();
    const int width = qMax(200, viewport()->width() - margins.left() - margins.right());
    for (QWidget *section :
         std::initializer_list<QWidget *>{m_emptyLabel, m_header, m_transform, m_filters})
        section->setFixedWidth(width);
    updateTitleElision();
}

void InspectorWidget::doRefresh()
{
    Mlt::Producer *producer = m_controller ? m_controller->attachedModel()->producer() : nullptr;
    if (producer && (!producer->is_valid() || producer->is_blank()))
        producer = nullptr;
    updateHeader(producer);
    updateTransform(producer);
    updateFilters();
    const bool hasProducerWidget = !m_producerWidget.isNull();
    m_properties->setVisible(hasProducerWidget);
    m_emptyLabel->setVisible(!producer && !hasProducerWidget);
}

void InspectorWidget::updateHeader(Mlt::Producer *producer)
{
    m_header->setVisible(producer);
    if (!producer) {
        m_thumbnailKey.clear();
        return;
    }
    m_titleText = Util::producerTitle(*producer);
    updateTitleElision();

    const QString service = QString::fromLatin1(producer->get("mlt_service"));
    bool audio = false;
    bool hasThumbnail = false;
    QString kind;
    QString size;
    if (producer->type() == mlt_service_tractor_type) {
        kind = tr("Timeline");
        size = QStringLiteral("%1×%2").arg(MLT.profile().width()).arg(MLT.profile().height());
    } else if (producer->type() == mlt_service_playlist_type) {
        audio = producer->get_int(kAudioTrackProperty);
        kind = audio ? tr("Audio track") : tr("Video track");
    } else if (producer->get(kShotcutTransitionProperty)
               || producer->parent().get(kShotcutTransitionProperty)) {
        kind = tr("Transition");
    } else {
        audio = isAudioOnly(*producer);
        if (audio)
            kind = tr("Audio");
        else if (MLT.isImageProducer(producer))
            kind = tr("Image");
        else if (service.startsWith("avformat"))
            kind = tr("Video");
        else
            kind = tr("Generator");
        hasThumbnail = !audio;
        Mlt::Producer parent(producer->get_parent());
        const int width = parent.get_int("meta.media.width");
        const int height = parent.get_int("meta.media.height");
        if (!audio && width > 0 && height > 0)
            size = QStringLiteral("%1×%2").arg(width).arg(height);
    }
    const int in = producer->get(kFilterInProperty) ? producer->get_int(kFilterInProperty)
                                                    : producer->get_in();
    const int out = producer->get(kFilterOutProperty) ? producer->get_int(kFilterOutProperty)
                                                      : producer->get_out();
    QStringList meta{kind};
    if (!size.isEmpty())
        meta << size;
    if (out >= in)
        meta << shortDuration(out - in + 1);
    m_meta->setText(meta.join(QStringLiteral(" · ")));

    // The thumbnail comes from the same cache as the timeline thumbnails.
    const QString key = hasThumbnail
                            ? QStringLiteral("%1/%2/%3#%4")
                                  .arg(QString::fromUtf8(producer->get(kShotcutHashProperty)),
                                       service,
                                       QString::fromUtf8(producer->get("resource")))
                                  .arg(in)
                            : QStringLiteral("placeholder:%1").arg(audio);
    if (key == m_thumbnailKey)
        return;
    m_thumbnailKey = key;
    m_thumbnail->setPixmap(thumbnailPixmap(QImage(), audio, devicePixelRatioF()));
    if (hasThumbnail) {
        m_thumbnailWatcher.setProperty("key", key);
        m_thumbnailWatcher.setFuture(QtConcurrent::run([key]() {
            ThumbnailProvider provider;
            QSize size;
            return provider.requestImage(key, &size, QSize(128, 72));
        }));
    }
}

void InspectorWidget::updateTitleElision()
{
    if (!m_title)
        return;
    const int width = qMax(20, m_header->width() - kThumbnailSize.width() - 10);
    m_title->setText(m_title->fontMetrics().elidedText(m_titleText, Qt::ElideMiddle, width));
    m_title->setToolTip(m_titleText);
}

void InspectorWidget::updateTransform(Mlt::Producer *producer)
{
    const bool visible = m_controller && isVisualClip(producer);
    m_transform->setVisible(visible);
    if (!visible)
        return;

    AttachedFiltersModel *model = m_controller->attachedModel();
    const QRectF base = defaultRect();
    QRectF rect = base;
    double rotation = 0.0;
    double opacity = 1.0;
    bool geometryKeyframed = false;
    bool rotationKeyframed = false;
    bool opacityKeyframed = false;
    int row = findFilter(kSizePositionId);
    if (row >= 0) {
        std::unique_ptr<Mlt::Service> service(model->getService(row));
        if (service && service->is_valid()) {
            const bool simple = hasSimpleKeyframes(*service);
            geometryKeyframed = simple || isKeyframed(*service, kRectProperty);
            rotationKeyframed = simple || isKeyframed(*service, kRotationProperty);
            const QRectF filterRect = serviceRect(*service, kRectProperty);
            if (filterRect.width() > 0 && filterRect.height() > 0)
                rect = filterRect;
            rotation = service->get_double(kRotationProperty);
        }
    }
    row = findFilter(kOpacityId);
    if (row >= 0) {
        std::unique_ptr<Mlt::Service> service(model->getService(row));
        if (service && service->is_valid()) {
            opacityKeyframed = hasSimpleKeyframes(*service) || isKeyframed(*service, "opacity");
            if (service->get("opacity"))
                opacity = service->get_double("opacity");
        }
    }
    // Keep the aspect ratio of the clip unless the rectangle was distorted on purpose
    // (rounding to whole pixels must not change it little by little).
    const double baseAspect = base.width() / qMax(1.0, base.height());
    m_aspectRatio = rect.width() / qMax(1.0, rect.height());
    if (qAbs(m_aspectRatio / baseAspect - 1.0) < 0.01)
        m_aspectRatio = baseAspect;

    // Do not fight the control that the user is dragging or typing in.
    m_updating = true;
    const QPointF offset = rect.center() - base.center();
    if (!m_positionX->hasFocus())
        m_positionX->setValue(qRound(offset.x()));
    if (!m_positionY->hasFocus())
        m_positionY->setValue(qRound(offset.y()));
    const int scale = qRound(rect.width() / qMax(1.0, base.width()) * 100.0);
    if (!m_scaleSlider->isSliderDown())
        m_scaleSlider->setValue(scale);
    if (!m_scaleValue->hasFocus())
        m_scaleValue->setValue(scale);
    if (!m_rotationSlider->isSliderDown())
        m_rotationSlider->setValue(qRound(rotation));
    if (!m_rotationValue->hasFocus())
        m_rotationValue->setValue(qRound(rotation));
    if (!m_opacitySlider->isSliderDown())
        m_opacitySlider->setValue(qRound(opacity * 100.0));
    if (!m_opacityValue->hasFocus())
        m_opacityValue->setValue(qRound(opacity * 100.0));
    m_updating = false;

    for (QWidget *w :
         std::initializer_list<QWidget *>{m_positionX, m_positionY, m_scaleSlider, m_scaleValue})
        w->setEnabled(!geometryKeyframed);
    m_rotationSlider->setEnabled(!rotationKeyframed);
    m_rotationValue->setEnabled(!rotationKeyframed);
    m_opacitySlider->setEnabled(!opacityKeyframed);
    m_opacityValue->setEnabled(!opacityKeyframed);
    m_transformHint->setVisible(geometryKeyframed || rotationKeyframed || opacityKeyframed);
}

void InspectorWidget::updateFilters()
{
    const bool visible = m_controller && m_controller->attachedModel()->isProducerSelected();
    m_filters->setVisible(visible);
    if (!visible)
        return;

    AttachedFiltersModel *model = m_controller->attachedModel();
    const int count = model->rowCount();
    const QString title = tr("Filters").toUpper();
    m_filtersLabel->setText(count ? QStringLiteral("%1 · %2").arg(title).arg(count) : title);
    while (m_filterRows.size() > count)
        delete m_filterRows.takeLast();
    while (m_filterRows.size() < count) {
        auto row = new InspectorFilterRow(m_filters);
        connect(row, &InspectorFilterRow::clicked, this, [this](int index) {
            m_controller->setCurrentFilter(index);
        });
        connect(row, &InspectorFilterRow::activated, this, [this](int index) {
            m_controller->setCurrentFilter(index);
            emit filtersPanelRequested();
        });
        connect(row, &InspectorFilterRow::toggled, this, [this](int index) {
            // Undoable, the same as the check box in the Filters panel.
            AttachedFiltersModel *model = m_controller->attachedModel();
            model->setData(model->index(index), QVariant(), Qt::CheckStateRole);
            refresh();
        });
        m_filterRowsLayout->addWidget(row);
        m_filterRows.append(row);
    }
    for (int i = 0; i < count; i++) {
        const QModelIndex index = model->index(i);
        QmlMetadata *meta = model->getMetadata(i);
        const QString name = model->data(index, Qt::DisplayRole).toString();
        InspectorFilterRow *row = m_filterRows[i];
        row->setRow(i);
        row->setName(name);
        row->setIcon(filterIcon(meta));
        // Links (time filters) cannot be disabled.
        row->setToggleVisible(!meta || meta->type() != QmlMetadata::Link);
        row->setEnabledFilter(model->data(index, Qt::CheckStateRole).toInt() == Qt::Checked);
        row->setCurrent(i == m_controller->currentIndex());
        row->setToolTip(
            tr("%1 (%2)\nDouble-click to edit it in the Filters panel.")
                .arg(name, model->data(index, AttachedFiltersModel::TypeDisplayRole).toString()));
    }
}

int InspectorWidget::findFilter(const QString &id) const
{
    AttachedFiltersModel *model = m_controller->attachedModel();
    for (int i = 0; i < model->rowCount(); i++) {
        QmlMetadata *meta = model->getMetadata(i);
        if (meta && meta->uniqueId() == id)
            return i;
    }
    return -1;
}

QRectF InspectorWidget::defaultRect() const
{
    // The rectangle that fits the clip in the video mode, as SizePositionUI.qml computes it.
    const double width = MLT.profile().width();
    const double height = MLT.profile().height();
    const double sar = MLT.profile().sar();
    const double profileDar = MLT.profile().dar();
    double dar = profileDar;
    Mlt::Producer *producer = m_controller ? m_controller->attachedModel()->producer() : nullptr;
    if (producer && producer->is_valid()) {
        Mlt::Producer parent(producer->get_parent());
        const double mediaWidth = parent.get_double("meta.media.width");
        const double mediaHeight = parent.get_double("meta.media.height");
        if (mediaWidth > 0 && mediaHeight > 0) {
            double aspect = 1.0;
            if (parent.get_double("meta.media.sample_aspect_den") > 0)
                aspect = parent.get_double("meta.media.sample_aspect_num")
                         / parent.get_double("meta.media.sample_aspect_den");
            if (aspect > 0)
                dar = aspect * mediaWidth / mediaHeight;
        }
    }
    QRectF rect;
    if (dar > profileDar) {
        rect.setWidth(width);
        rect.setHeight(width * sar / dar);
    } else {
        rect.setHeight(height);
        rect.setWidth(height / sar * dar);
    }
    rect.setSize(QSizeF(qRound(rect.width()), qRound(rect.height())));
    rect.moveTo(qRound((width - rect.width()) / 2.0), qRound((height - rect.height()) / 2.0));
    return rect;
}

QmlFilter *InspectorWidget::beginEdit(const QString &id, const QString &description)
{
    if (!m_controller)
        return nullptr;
    AttachedFiltersModel *model = m_controller->attachedModel();
    int row = findFilter(id);
    bool added = false;
    if (row < 0) {
        // The first change adds the filter (undoable like "+" in the Filters panel).
        QmlMetadata *meta = m_controller->metadata(id);
        if (!meta)
            return nullptr;
        row = model->add(meta);
        if (row < 0 || findFilter(id) != row)
            return nullptr;
        added = true;
    }
    // Edit through the current filter: its changes are undoable and the
    // Filters panel shows them.
    m_controller->setCurrentFilter(row);
    QmlFilter *filter = m_controller->currentFilter();
    if (!filter || !filter->service().is_valid())
        return nullptr;
    if (added) {
        setFilterDefaults(id, filter->service());
        // Include the defaults in the state that undo returns to.
        if (!model->isSourceClip())
            filter->startUndoTracking();
    }
    filter->startUndoParameterCommand(description);
    return filter;
}

void InspectorWidget::setFilterDefaults(const QString &id, Mlt::Service &service)
{
    // The values that the filter user interface sets for a new filter; the
    // Filters panel may not have loaded it (it is behind another tab).
    if (id == kSizePositionId) {
        if (!service.get(kRectProperty)) {
            const QRectF rect = defaultRect();
            service.set(kRectProperty, rect.x(), rect.y(), rect.width(), rect.height(), 1.0);
        }
        if (!service.get("transition.fill"))
            service.set("transition.fill", 1);
        if (!service.get("transition.distort"))
            service.set("transition.distort", 0);
        if (!service.get("transition.halign"))
            service.set("transition.halign", "center");
        if (!service.get("transition.valign"))
            service.set("transition.valign", "middle");
        if (!service.get(kRotationProperty))
            service.set(kRotationProperty, 0);
        if (!service.get("background"))
            service.set("background", "color:#00000000");
        if (!service.get("transition.threads"))
            service.set("transition.threads", 0);
    } else if (id == kOpacityId) {
        if (!service.get("start"))
            service.set("start", 1);
        if (!service.get("level"))
            service.set("level", 1);
        if (!service.get("alpha"))
            service.set("alpha", 1.0);
        if (!service.get("opacity"))
            service.set("opacity", 1.0);
    }
}

// The integer closest to target with the parity of reference: centering it on the
// center of reference keeps integer coordinates, so the position does not drift.
static double sameParity(double target, double reference)
{
    return qMax(reference - 2.0 * qRound((reference - target) / 2.0),
                2.0 - std::fmod(reference, 2.0));
}

void InspectorWidget::applyGeometry(const QString &description)
{
    const QRectF base = defaultRect();
    const double width = sameParity(base.width() * m_scaleValue->value() / 100.0, base.width());
    const double height = sameParity(width / qMax(0.01, m_aspectRatio), base.height());
    QRectF rect(0, 0, width, height);
    rect.moveCenter(base.center() + QPointF(m_positionX->value(), m_positionY->value()));
    if (QmlFilter *filter = beginEdit(kSizePositionId, description)) {
        filter->set(kRectProperty, rect);
        filter->set(kMiddleValue, rect);
        filter->endUndoCommand();
    }
}

void InspectorWidget::applyRotation(int degrees)
{
    if (QmlFilter *filter = beginEdit(kSizePositionId, tr("Rotation"))) {
        filter->set(kRotationProperty, double(degrees));
        filter->set(kRotationMiddleValue, double(degrees));
        filter->endUndoCommand();
    }
}

void InspectorWidget::applyOpacity(int percent)
{
    if (QmlFilter *filter = beginEdit(kOpacityId, tr("Opacity"))) {
        const double value = percent / 100.0;
        filter->set("alpha", value);
        filter->set("opacity", value);
        filter->endUndoCommand();
    }
}

QIcon InspectorWidget::filterIcon(QmlMetadata *meta)
{
    auto it = m_icons.constFind(meta);
    if (it != m_icons.constEnd())
        return it.value();
    QIcon icon;
    if (meta) {
        QString path = meta->iconFilePath();
        if (path.startsWith("qrc:"))
            path = path.mid(3);
        else if (!path.isEmpty())
            path = QUrl(path).toLocalFile();
        const QImage image(path);
        if (!image.isNull())
            icon = QIcon(QPixmap::fromImage(image));
    }
    if (icon.isNull())
        icon = QIcon::fromTheme("view-filter", QIcon(":/icons/dark/32x32/view-filter.png"));
    m_icons.insert(meta, icon);
    return icon;
}

QLabel *InspectorWidget::createSectionLabel(const QString &text, const char *name)
{
    // Section labels: uppercase with tracking (plan.md 3.2, item 4).
    auto label = new QLabel(text.toUpper());
    label->setObjectName(name);
    label->setProperty("inspectorSection", true);
    QFont font = label->font();
    font.setPixelSize(11);
    font.setWeight(QFont::DemiBold);
    font.setLetterSpacing(QFont::AbsoluteSpacing, 0.8);
    label->setFont(font);
    return label;
}

QFrame *InspectorWidget::createDivider()
{
    auto divider = new QFrame;
    divider->setObjectName("inspectorDivider");
    divider->setFixedHeight(1);
    return divider;
}
