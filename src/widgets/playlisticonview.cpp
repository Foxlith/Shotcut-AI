/*
 * Copyright (c) 2016-2026 Meltytech, LLC
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

#include "playlisticonview.h"

#include "Logger.h"
#include "models/playlistmodel.h"
#include "settings.h"

#include <QDebug>
#include <QMouseEvent>
#include <QPainter>
#include <QPainterPath>
#include <QRegularExpression>
#include <QScrollBar>
#include <QSortFilterProxyModel>
#include <QtMath>

static const auto kPaddingPx = 10;
static const auto kFilesSizeFactor = 1.5f;

// Grafito media grid (plan.md, section 3.2 item 2 and the "Tarjeta de Medio" row
// of the component catalog).
static const int kCardGap = 8;
static const int kCardMargin = 2; // room for the 2 px selection ring
static const int kCardMinWidth = 120;
static const int kCardTextHeight = 42;
static const qreal kCardRadius = 8.0;
static const QColor kCardPanel(0x15, 0x17, 0x1C);
static const QColor kCardSurface(0x1D, 0x20, 0x27);
static const QColor kCardBorder(0x22, 0x25, 0x2D);
static const QColor kCardHoverSurface(0x26, 0x2A, 0x33);
static const QColor kCardHoverBorder(0x34, 0x39, 0x44);
static const QColor kCardThumbBackground(0x0F, 0x11, 0x15);
static const QColor kCardText(0xE8, 0xEA, 0xEE);
static const QColor kCardSubtext(0x85, 0x8C, 0x98);
static const QColor kCardDisabledText(0x5F, 0x66, 0x72);
static const QColor kCardChip(11, 12, 15, 200);
static const QColor kCardWaveform(0x3D, 0xD6, 0xB0, 217);

// "00:00:06.000" (clock) or "00:00:06:00" (timecode) -> "00:06"; frames stay as they are.
static QString shortDuration(const QString &duration)
{
    QStringList parts = duration.split(QRegularExpression("[:;]"));
    if (parts.size() < 3)
        return duration;
    parts = parts.mid(0, 3);
    parts[2] = parts[2].section('.', 0, 0).section(',', 0, 0);
    if (parts[0].toInt() == 0)
        parts.removeFirst();
    return parts.join(':');
}

PlaylistIconView::PlaylistIconView(QWidget *parent)
    : QAbstractItemView(parent)
    , m_gridSize(170, 100)
    , m_draggingOverPos(QPoint())
    , m_itemsPerRow(3)
    , m_iconRole(Qt::DecorationRole)
{
    verticalScrollBar()->setSingleStep(100);
    verticalScrollBar()->setPageStep(400);
    setContextMenuPolicy(Qt::CustomContextMenu);
    connect(&Settings, SIGNAL(playlistThumbnailsChanged()), SLOT(updateSizes()));
}

bool PlaylistIconView::event(QEvent *event)
{
    // Accept ShortcutOverride for Left/Right so Qt delivers them as normal
    // KeyPress events to this widget instead of firing window-level shortcuts
    // (e.g. playerNextFrameAction / playerPreviousFrameAction in player.cpp).
    if (event->type() == QEvent::ShortcutOverride) {
        auto *ke = static_cast<QKeyEvent *>(event);
        if (ke->key() == Qt::Key_Left || ke->key() == Qt::Key_Right) {
            ke->accept();
            return true;
        }
    } else if (event->type() == QEvent::PaletteChange) {
        // The card layout follows the theme (see isCardLayout()).
        updateSizes();
    }
    return QAbstractItemView::event(event);
}

void PlaylistIconView::setCardMode(bool enabled)
{
    m_cardMode = enabled;
    viewport()->setMouseTracking(enabled);
    setFrameShape(enabled ? QFrame::NoFrame : QFrame::StyledPanel);
    updateSizes();
}

bool PlaylistIconView::isCardLayout() const
{
    return m_cardMode && Settings.isGrafito();
}

QRect PlaylistIconView::cardRect(const QRect &cell) const
{
    return QRect(cell.topLeft() + QPoint(kCardMargin, kCardMargin), m_cardSize);
}

QRect PlaylistIconView::_visualRect(const QModelIndex &index) const
{
    if (!index.isValid())
        return QRect();
    int row = index.row() / m_itemsPerRow;
    int col = index.row() % m_itemsPerRow;
    return QRect(col * m_gridSize.width(),
                 row * m_gridSize.height(),
                 m_gridSize.width(),
                 m_gridSize.height());
}

QRect PlaylistIconView::visualRect(const QModelIndex &index) const
{
    // TODO: this was causing a performance problem
    // return _visualRect(index);
    return QRect();
}

void PlaylistIconView::rowsInserted(const QModelIndex &parent, int start, int end)
{
    QAbstractItemView::rowsInserted(parent, start, end);
    updateSizes();
}

void PlaylistIconView::rowsAboutToBeRemoved(const QModelIndex &parent, int start, int end)
{
    QAbstractItemView::rowsAboutToBeRemoved(parent, start, end);
    updateSizes();
}

void PlaylistIconView::dataChanged(const QModelIndex &topLeft,
                                   const QModelIndex &bottomRight,
                                   const QVector<int> &roles)
{
    QAbstractItemView::dataChanged(topLeft, bottomRight, roles);
    updateSizes();
}

void PlaylistIconView::selectionChanged(const QItemSelection &selected,
                                        const QItemSelection &deselected)
{
    QAbstractItemView::selectionChanged(selected, deselected);
    viewport()->update();
}

void PlaylistIconView::scrollTo(const QModelIndex &index, ScrollHint hint)
{
    Q_UNUSED(hint);
    if (!index.isValid() || !verticalScrollBar())
        return;
    const QRect rect = _visualRect(index);
    const int viewTop = verticalScrollBar()->value();
    const int viewBottom = viewTop + viewport()->height();
    if (rect.top() < viewTop)
        verticalScrollBar()->setValue(rect.top());
    else if (rect.bottom() > viewBottom)
        verticalScrollBar()->setValue(rect.bottom() - viewport()->height());
}

QModelIndex PlaylistIconView::indexAt(const QPoint &point) const
{
    if (!model())
        return QModelIndex();

    if (point.x() / m_gridSize.width() >= m_itemsPerRow)
        return QModelIndex();

    int row = (point.y() + verticalScrollBar()->value()) / m_gridSize.height();
    int col = (point.x() / m_gridSize.width()) % m_itemsPerRow;
    return model()->index(row * m_itemsPerRow + col, 0, rootIndex());
}

QModelIndex PlaylistIconView::moveCursor(CursorAction cursorAction, Qt::KeyboardModifiers modifiers)
{
    Q_UNUSED(modifiers);
    if (!model())
        return QModelIndex();
    const int count = model()->rowCount(rootIndex());
    if (count == 0)
        return QModelIndex();
    const QModelIndex current = currentIndex();
    int row = current.isValid() ? current.row() : 0;
    switch (cursorAction) {
    case MoveLeft:
        row = qMax(0, row - 1);
        break;
    case MoveRight:
        row = qMin(count - 1, row + 1);
        break;
    case MoveUp:
        row = qMax(0, row - m_itemsPerRow);
        break;
    case MoveDown:
        row = qMin(count - 1, row + m_itemsPerRow);
        break;
    case MoveHome:
        row = 0;
        break;
    case MoveEnd:
        row = count - 1;
        break;
    case MoveNext:
        row = qMin(count - 1, row + 1);
        break;
    case MovePrevious:
        row = qMax(0, row - 1);
        break;
    default:
        break;
    }
    return model()->index(row, 0, rootIndex());
}

int PlaylistIconView::horizontalOffset() const
{
    return 0;
}

int PlaylistIconView::verticalOffset() const
{
    return 0;
}

bool PlaylistIconView::isIndexHidden(const QModelIndex &index) const
{
    Q_UNUSED(index);
    return false;
}

void PlaylistIconView::setSelection(const QRect &rect, QItemSelectionModel::SelectionFlags command)
{
    // A null rect comes from keyboard navigation because visualRect() returns QRect().
    // The force-select in keyPressEvent handles selection after the base class finishes.
    if (rect.isNull())
        return;

    QModelIndex topLeft;
    if (!selectionModel()->selectedIndexes().isEmpty()) {
        topLeft = selectionModel()->selectedIndexes().first();
    } else if (!m_isRangeSelect) {
        selectionModel()->select(indexAt(rect.topLeft()), command);
        return;
    }
    if (m_isToggleSelect) {
        command = QItemSelectionModel::Select;
        selectionModel()->select(indexAt(rect.bottomRight()), command);
        return;
    } else if (m_isRangeSelect && topLeft.isValid()) {
        QModelIndex bottomRight = indexAt(rect.bottomRight());
        selectionModel()->select(QItemSelection(topLeft, bottomRight), command);
        return;
    } else if (topLeft.isValid()) {
        selectionModel()->select(indexAt(rect.topLeft()), command);
        return;
    }
    m_pendingSelect = indexAt(rect.topLeft());
}

QRegion PlaylistIconView::visualRegionForSelection(const QItemSelection &selection) const
{
    Q_UNUSED(selection);
    return QRegion();
}

void PlaylistIconView::currentChanged(const QModelIndex &current, const QModelIndex &previous)
{
    viewport()->update();
    QAbstractItemView::currentChanged(current, previous);
}

void PlaylistIconView::paintEvent(QPaintEvent *)
{
    QPainter painter(viewport());
    QPalette pal(palette());
    const auto proxy = tr("P", "The first letter or symbol of \"proxy\"");
    const auto oldFont = painter.font();
    auto boldFont(oldFont);

    painter.setRenderHints(QPainter::TextAntialiasing | QPainter::SmoothPixmapTransform);
    boldFont.setBold(true);
    painter.fillRect(rect(), pal.base());

    if (!model())
        return;

    auto proxyModel = static_cast<QSortFilterProxyModel *>(model());
    QRect dragIndicator;

    if (isCardLayout()) {
        painter.fillRect(rect(), kCardPanel);
        painter.setRenderHint(QPainter::Antialiasing);
        const int count = proxyModel->rowCount(rootIndex());
        for (int i = 0; i < count; i++) {
            const QRect cell((i % m_itemsPerRow) * m_gridSize.width(),
                             (i / m_itemsPerRow) * m_gridSize.height()
                                 - verticalScrollBar()->value(),
                             m_gridSize.width(),
                             m_gridSize.height());
            if (cell.bottom() < 0)
                continue;
            if (cell.top() > viewport()->height())
                break;
            const QModelIndex idx = proxyModel->index(i, 0, rootIndex());
            const QRect card = cardRect(cell);
            paintCard(painter, idx, card);
            if (!m_draggingOverPos.isNull() && cell.contains(m_draggingOverPos)) {
                const auto dropPos = position(m_draggingOverPos, cell, idx);
                const int x = (dropPos == QAbstractItemView::AboveItem)
                                  ? card.left() - kCardGap / 2 - 1
                                  : card.right() + kCardGap / 2;
                dragIndicator = QRect(x, card.top(), 2, card.height());
            }
        }
        if (!dragIndicator.isNull())
            painter.fillRect(dragIndicator, pal.highlight());
        return;
    }

    for (int row = 0; row <= proxyModel->rowCount(rootIndex()) / m_itemsPerRow; row++) {
        for (int col = 0; col < m_itemsPerRow; col++) {
            const int rowIdx = row * m_itemsPerRow + col;

            QModelIndex idx = proxyModel->index(rowIdx, 0, rootIndex());
            if (!idx.isValid())
                break;

            QRect itemRect(col * m_gridSize.width(),
                           row * m_gridSize.height() - verticalScrollBar()->value(),
                           m_gridSize.width(),
                           m_gridSize.height());

            if (itemRect.bottom() < 0 || itemRect.top() > this->height())
                continue;

            const bool selected = selectedIndexes().contains(idx);
            QImage thumb = proxyModel->mapToSource(idx).data(m_iconRole).value<QImage>();

            if (m_iconRole != Qt::DecorationRole) { // Files
                thumb = thumb.scaled(PlaylistModel::THUMBNAIL_WIDTH * kFilesSizeFactor,
                                     PlaylistModel::THUMBNAIL_HEIGHT * kFilesSizeFactor,
                                     Qt::KeepAspectRatio,
                                     Qt::SmoothTransformation);
            }

            QRect imageBoundingRect = itemRect;
            imageBoundingRect.setHeight(0.7 * imageBoundingRect.height());
            imageBoundingRect.adjust(0, kPaddingPx, 0, 0);

            QRect imageRect(QPoint(), thumb.size());
            imageRect.moveCenter(imageBoundingRect.center());

            QRect textRect = itemRect;
            textRect.setTop(imageBoundingRect.bottom());
            textRect.adjust(3, 0, -3, 0);

            QRect buttonRect = itemRect.adjusted(2, 2, -2, -2);

            if (selected) {
                painter.fillRect(buttonRect, pal.highlight());
            } else {
                painter.fillRect(buttonRect, pal.button());

                painter.setPen(pal.color(QPalette::Button).lighter());
                painter.drawLine(buttonRect.topLeft(), buttonRect.topRight());
                painter.drawLine(buttonRect.topLeft(), buttonRect.bottomLeft());

                painter.setPen(pal.color(QPalette::Button).darker());
                painter.drawLine(buttonRect.topRight(), buttonRect.bottomRight());
                painter.drawLine(buttonRect.bottomLeft(), buttonRect.bottomRight());
            }

            painter.drawImage(imageRect, thumb);
            QStringList nameParts
                = proxyModel->mapToSource(idx).data(Qt::DisplayRole).toString().split('\n');
            if (nameParts.size() > 1) {
                const auto indexPos = imageRect.topLeft() + QPoint(5, 15);
                painter.setFont(boldFont);
                painter.setPen(pal.color(QPalette::Dark).darker());
                painter.drawText(indexPos, proxy);
                painter.setPen(pal.color(QPalette::WindowText));
                painter.drawText(indexPos - QPoint(1, 1), proxy);
                painter.setFont(oldFont);
            }
            painter.setPen(pal.color(QPalette::WindowText));
            painter.drawText(textRect,
                             Qt::AlignCenter,
                             painter.fontMetrics().elidedText(nameParts.first(),
                                                              m_elideMode,
                                                              textRect.width()));

            if (!m_draggingOverPos.isNull() && itemRect.contains(m_draggingOverPos)) {
                QAbstractItemView::DropIndicatorPosition dropPos = position(m_draggingOverPos,
                                                                            itemRect,
                                                                            idx);
                dragIndicator.setSize(QSize(4, itemRect.height()));
                if (dropPos == QAbstractItemView::AboveItem)
                    dragIndicator.moveTopLeft(itemRect.topLeft()
                                              - QPoint(dragIndicator.width() / 2, 0));
                else
                    dragIndicator.moveTopLeft(itemRect.topRight()
                                              - QPoint(dragIndicator.width() / 2 - 1, 0));
            }
        }
    }
    if (!dragIndicator.isNull()) {
        painter.fillRect(dragIndicator, pal.buttonText());
    }
}

void PlaylistIconView::paintCard(QPainter &painter, const QModelIndex &idx, const QRect &card)
{
    auto proxyModel = static_cast<QSortFilterProxyModel *>(model());
    const QModelIndex source = proxyModel->mapToSource(idx);
    const QColor accent = palette().color(QPalette::Highlight);
    const bool enabled = isEnabled();
    const bool selected = selectionModel() && selectionModel()->isSelected(idx);
    const bool hovered = enabled && m_hoverIndex == idx;
    const bool focused = hasFocus() && currentIndex() == idx;

    painter.save();
    if (!enabled)
        painter.setOpacity(0.5);

    // Card: #1D2027 surface, 1 px #22252D border, 8 px radius.
    const QRectF cardF = QRectF(card).adjusted(0.5, 0.5, -0.5, -0.5);
    if (selected || focused) {
        QColor ring = accent;
        if (!focused)
            ring.setAlphaF(0.18);
        painter.setPen(QPen(ring, 2));
        painter.setBrush(Qt::NoBrush);
        painter.drawRoundedRect(cardF.adjusted(-1.5, -1.5, 1.5, 1.5),
                                kCardRadius + 1.5,
                                kCardRadius + 1.5);
    }
    painter.setPen(QPen(selected ? accent : (hovered ? kCardHoverBorder : kCardBorder), 1));
    painter.setBrush(hovered ? kCardHoverSurface : kCardSurface);
    painter.drawRoundedRect(cardF, kCardRadius, kCardRadius);

    // 16:9 thumbnail with rounded top corners.
    const int type = source.data(PlaylistModel::FIELD_MEDIA_TYPE_ENUM).toInt();
    const QRectF thumbRect(card.x() + 1,
                           card.y() + 1,
                           card.width() - 2,
                           qRound((card.width() - 2) * 9.0 / 16.0));
    QPainterPath roundedTop;
    roundedTop.addRoundedRect(thumbRect, kCardRadius - 1, kCardRadius - 1);
    QPainterPath squareBottom;
    squareBottom.addRect(thumbRect.adjusted(0, thumbRect.height() / 2, 0, 0));
    painter.save();
    painter.setClipPath(roundedTop.united(squareBottom));
    painter.fillRect(thumbRect, kCardThumbBackground);
    const QImage thumb = source.data(PlaylistModel::FIELD_CARD_THUMBNAIL).value<QImage>();
    if (type != PlaylistModel::Audio && !thumb.isNull()) {
        // Fill the frame, cropping the image if its aspect ratio is not 16:9.
        QRectF target(QPointF(),
                      QSizeF(thumb.size()).scaled(thumbRect.size(), Qt::KeepAspectRatioByExpanding));
        target.moveCenter(thumbRect.center());
        painter.drawImage(target, thumb);
    } else if (type == PlaylistModel::Audio) {
        // Waveform glyph in the audio clip color of the timeline.
        static const qreal levels[]
            = {0.35, 0.6, 0.9, 0.5, 0.75, 1.0, 0.55, 0.8, 0.4, 0.7, 0.95, 0.5, 0.65, 0.3, 0.45};
        const int bars = int(sizeof(levels) / sizeof(levels[0]));
        const qreal barWidth = 3.0;
        const qreal step = 5.0;
        const qreal x0 = thumbRect.center().x() - (bars * step - (step - barWidth)) / 2.0;
        painter.setPen(Qt::NoPen);
        painter.setBrush(kCardWaveform);
        for (int i = 0; i < bars; i++) {
            const qreal h = thumbRect.height() * 0.5 * levels[i];
            painter
                .drawRoundedRect(QRectF(x0 + i * step, thumbRect.center().y() - h / 2, barWidth, h),
                                 1.5,
                                 1.5);
        }
    } else {
        // Frame glyph while the thumbnail is not available (or thumbnails are hidden).
        const QRectF glyph(thumbRect.center() - QPointF(12, 9), QSizeF(24, 18));
        painter.setPen(QPen(kCardDisabledText, 1.5));
        painter.setBrush(Qt::NoBrush);
        painter.drawRoundedRect(glyph, 3, 3);
        QPolygonF triangle;
        triangle << glyph.center() + QPointF(-3, -4.5) << glyph.center() + QPointF(5, 0)
                 << glyph.center() + QPointF(-3, 4.5);
        painter.setBrush(kCardDisabledText);
        painter.drawPolygon(triangle);
    }
    painter.restore();

    const QStringList nameParts = source.data(Qt::DisplayRole).toString().split('\n');
    QFont chipFont = font();
    chipFont.setFamilies({QStringLiteral("Geist Mono"), QStringLiteral("DejaVu Sans Mono")});
    chipFont.setStyleHint(QFont::Monospace);
    chipFont.setPixelSize(10);
    chipFont.setWeight(QFont::Medium);
    const QFontMetrics chipMetrics(chipFont);
    painter.setFont(chipFont);

    // Duration chip in the bottom right corner of the thumbnail.
    const QString duration = shortDuration(source.data(PlaylistModel::FIELD_DURATION).toString());
    if (!duration.isEmpty()) {
        QRectF chip(0, 0, chipMetrics.horizontalAdvance(duration) + 10, chipMetrics.height() + 2);
        chip.moveBottomRight(thumbRect.bottomRight() - QPointF(5, 5));
        painter.setPen(Qt::NoPen);
        painter.setBrush(kCardChip);
        painter.drawRoundedRect(chip, 4, 4);
        painter.setPen(kCardText);
        painter.drawText(chip, Qt::AlignCenter, duration);
    }
    // Proxy badge in the top left corner.
    if (nameParts.size() > 1) {
        const auto proxy = tr("P", "The first letter or symbol of \"proxy\"");
        QRectF chip(0, 0, chipMetrics.horizontalAdvance(proxy) + 10, chipMetrics.height() + 2);
        chip.moveTopLeft(thumbRect.topLeft() + QPointF(5, 5));
        painter.setPen(Qt::NoPen);
        painter.setBrush(kCardChip);
        painter.drawRoundedRect(chip, 4, 4);
        painter.setPen(accent);
        painter.drawText(chip, Qt::AlignCenter, proxy);
    }

    // Name and type.
    QFont nameFont = font();
    nameFont.setPixelSize(12);
    nameFont.setWeight(QFont::Medium);
    painter.setFont(nameFont);
    painter.setPen(enabled ? kCardText : kCardDisabledText);
    const QRect nameRect(card.x() + 8, qRound(thumbRect.bottom()) + 5, card.width() - 16, 17);
    painter.drawText(nameRect,
                     Qt::AlignLeft | Qt::AlignVCenter,
                     painter.fontMetrics().elidedText(nameParts.first(),
                                                      m_elideMode,
                                                      nameRect.width()));
    QFont typeFont = font();
    typeFont.setPixelSize(11);
    painter.setFont(typeFont);
    painter.setPen(enabled ? kCardSubtext : kCardDisabledText);
    const QRect typeRect(nameRect.x(), nameRect.bottom() + 1, nameRect.width(), 15);
    painter.drawText(typeRect,
                     Qt::AlignLeft | Qt::AlignVCenter,
                     painter.fontMetrics()
                         .elidedText(source.data(PlaylistModel::FIELD_MEDIA_TYPE).toString(),
                                     Qt::ElideRight,
                                     typeRect.width()));
    painter.restore();
}

void PlaylistIconView::mouseMoveEvent(QMouseEvent *event)
{
    QAbstractItemView::mouseMoveEvent(event);
    if (!isCardLayout())
        return;
    const QPoint pos = event->position().toPoint();
    QModelIndex index = indexAt(pos);
    if (index.isValid()) {
        const int row = index.row() / m_itemsPerRow;
        const int col = index.row() % m_itemsPerRow;
        const QRect cell(col * m_gridSize.width(),
                         row * m_gridSize.height() - verticalScrollBar()->value(),
                         m_gridSize.width(),
                         m_gridSize.height());
        if (!cardRect(cell).contains(pos))
            index = QModelIndex();
    }
    if (index != QModelIndex(m_hoverIndex)) {
        m_hoverIndex = index;
        viewport()->update();
    }
}

bool PlaylistIconView::viewportEvent(QEvent *event)
{
    if (event->type() == QEvent::Leave && m_hoverIndex.isValid()) {
        m_hoverIndex = QModelIndex();
        viewport()->update();
    }
    return QAbstractItemView::viewportEvent(event);
}

void PlaylistIconView::mouseReleaseEvent(QMouseEvent *event)
{
    if (event->button() == Qt::LeftButton) {
        if (m_draggingOverPos.isNull() && m_pendingSelect.isValid()) {
            selectionModel()->select(m_pendingSelect, QItemSelectionModel::ClearAndSelect);
            viewport()->update();
        }
        m_pendingSelect = QModelIndex();
    }
    QAbstractItemView::mouseReleaseEvent(event);
}

void PlaylistIconView::dragMoveEvent(QDragMoveEvent *e)
{
    m_draggingOverPos = e->position().toPoint();
    QAbstractItemView::dragMoveEvent(e);
}

void PlaylistIconView::dragLeaveEvent(QDragLeaveEvent *e)
{
    m_draggingOverPos = QPoint();
    QAbstractItemView::dragLeaveEvent(e);
}

void PlaylistIconView::dropEvent(QDropEvent *event)
{
    m_draggingOverPos = QPoint();

    QModelIndex index = indexAt(event->position().toPoint());
    QRect rectAtDropPoint = _visualRect(index);

    QAbstractItemView::DropIndicatorPosition dropPos = position(event->position().toPoint(),
                                                                rectAtDropPoint,
                                                                index);
    if (dropPos == QAbstractItemView::BelowItem)
        index = index.sibling(index.row() + 1, index.column());

    const Qt::DropAction action = event->dropAction();
    int row = (index.row() != -1) ? index.row() : model()->rowCount(rootIndex());
    if (model()->dropMimeData(event->mimeData(), action, row, index.column(), index))
        event->acceptProposedAction();

    stopAutoScroll();
    setState(NoState);
    viewport()->update();
}

void PlaylistIconView::resizeEvent(QResizeEvent *event)
{
    updateSizes();
    QAbstractItemView::resizeEvent(event);
}

void PlaylistIconView::setModel(QAbstractItemModel *model)
{
    QAbstractItemView::setModel(model);
    updateSizes();
}

void PlaylistIconView::keyPressEvent(QKeyEvent *event)
{
    m_isToggleSelect = (event->modifiers() & Qt::ControlModifier);
    m_isRangeSelect = (event->modifiers() & Qt::ShiftModifier);

    QAbstractItemView::keyPressEvent(event);
    // Qt's internal setSelection() cannot work because visualRect() returns QRect().
    // Force the selection to match the new current index after all internal handling.
    if (!m_isToggleSelect && !m_isRangeSelect) {
        const QModelIndex cur = currentIndex();
        if (cur.isValid())
            selectionModel()->select(cur, QItemSelectionModel::ClearAndSelect);
    }
    // Accept navigation keys so the parent scroll area does not also handle them.
    // Other keys (Delete, Escape, etc.) are ignored so dock shortcuts can fire.
    switch (event->key()) {
    case Qt::Key_Left:
    case Qt::Key_Right:
    case Qt::Key_Up:
    case Qt::Key_Down:
    case Qt::Key_Home:
    case Qt::Key_End:
    case Qt::Key_PageUp:
    case Qt::Key_PageDown:
        event->accept();
        break;
    default:
        event->ignore();
        break;
    }
}

void PlaylistIconView::keyReleaseEvent(QKeyEvent *event)
{
    QAbstractItemView::keyReleaseEvent(event);
    event->ignore();
    resetMultiSelect();
}

QAbstractItemView::DropIndicatorPosition PlaylistIconView::position(const QPoint &pos,
                                                                    const QRect &rect,
                                                                    const QModelIndex &index) const
{
    Q_UNUSED(index);
    if (pos.x() < rect.center().x())
        return QAbstractItemView::AboveItem;
    else
        return QAbstractItemView::BelowItem;
}

void PlaylistIconView::updateSizes()
{
    if (!model() || !model()->rowCount(rootIndex())) {
        verticalScrollBar()->setRange(0, 0);
        return;
    }

    if (isCardLayout()) {
        // Two columns in the 300 px Media panel, more when the panel is wider.
        const int width = qMax(1, viewport()->width() - 2 * kCardMargin);
        m_itemsPerRow = qMax(1, (width + kCardGap) / (kCardMinWidth + kCardGap));
        const int cardWidth = qMax(1, (width - (m_itemsPerRow - 1) * kCardGap) / m_itemsPerRow);
        m_cardSize = QSize(cardWidth, qRound((cardWidth - 2) * 9.0 / 16.0) + 2 + kCardTextHeight);
        m_gridSize = QSize(cardWidth + kCardGap, m_cardSize.height() + kCardGap);
        const int rows = (model()->rowCount(rootIndex()) + m_itemsPerRow - 1) / m_itemsPerRow;
        verticalScrollBar()->setRange(0,
                                      qMax(0,
                                           rows * m_gridSize.height() - kCardGap + 2 * kCardMargin
                                               - viewport()->height()));
        verticalScrollBar()->setPageStep(viewport()->height());
        verticalScrollBar()->setSingleStep(m_gridSize.height() / 2);
        viewport()->update();
        return;
    }
    verticalScrollBar()->setSingleStep(100);
    verticalScrollBar()->setPageStep(400);

    QSize size;
    if (m_iconRole != Qt::DecorationRole) // Files
        size = QSize(PlaylistModel::THUMBNAIL_WIDTH * kFilesSizeFactor,
                     PlaylistModel::THUMBNAIL_HEIGHT * kFilesSizeFactor);
    else if (Settings.playlistThumbnails() == "tall")
        size = QSize(PlaylistModel::THUMBNAIL_WIDTH, PlaylistModel::THUMBNAIL_HEIGHT * 2);
    else if (Settings.playlistThumbnails() == "large")
        size = QSize(PlaylistModel::THUMBNAIL_WIDTH * 2, PlaylistModel::THUMBNAIL_HEIGHT * 2);
    else if (Settings.playlistThumbnails() == "wide")
        size = QSize(PlaylistModel::THUMBNAIL_WIDTH * 2, PlaylistModel::THUMBNAIL_HEIGHT);
    else
        size = QSize(PlaylistModel::THUMBNAIL_WIDTH, PlaylistModel::THUMBNAIL_HEIGHT);

    size.setWidth(size.width() + kPaddingPx);

    m_itemsPerRow = qMax(1, viewport()->width() / size.width());
    m_gridSize = QSize(viewport()->width() / m_itemsPerRow, size.height() + 40);

    if (!verticalScrollBar())
        return;

    verticalScrollBar()->setRange(0,
                                  m_gridSize.height() * model()->rowCount(rootIndex())
                                          / m_itemsPerRow
                                      - height() + m_gridSize.height());
    viewport()->update();
}

void PlaylistIconView::resetMultiSelect()
{
    m_isToggleSelect = false;
    m_isRangeSelect = false;
}

void PlaylistIconView::setIconRole(int role)
{
    m_iconRole = role;
}
