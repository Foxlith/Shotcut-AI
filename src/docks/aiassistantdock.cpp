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

#include "aiassistantdock.h"

#include "Logger.h"
#include "ai/aitools.h"
#include "ai/clientsetup.h"
#include "aiagentserver.h"
#include "settings.h"
#include "util.h"

#include <QApplication>
#include <QClipboard>
#include <QDir>
#include <QFileInfo>
#include <QGuiApplication>
#include <QHBoxLayout>
#include <QKeyEvent>
#include <QLabel>
#include <QListWidget>
#include <QMenu>
#include <QMessageBox>
#include <QMouseEvent>
#include <QPainter>
#include <QProcess>
#include <QPushButton>
#include <QScrollArea>
#include <QStandardPaths>
#include <QTimer>
#include <QToolButton>
#include <QUndoStack>
#include <QVBoxLayout>

// A client that talked to the server in the last minutes counts as connected.
static const qint64 kConnectedSeconds = 10 * 60;

static QLabel *sectionTitle(const QString &text)
{
    auto label = new QLabel(text);
    auto font = label->font();
    font.setBold(true);
    font.setPointSizeF(font.pointSizeF() * 1.1);
    label->setFont(font);
    return label;
}

static QPixmap dot(const QColor &color, int size)
{
    const qreal ratio = qApp->devicePixelRatio();
    QPixmap pixmap(QSize(size, size) * ratio);
    pixmap.setDevicePixelRatio(ratio);
    pixmap.fill(Qt::transparent);
    QPainter painter(&pixmap);
    painter.setRenderHint(QPainter::Antialiasing);
    painter.setPen(Qt::NoPen);
    painter.setBrush(color);
    painter.drawEllipse(QRectF(1, 1, size - 2, size - 2));
    return pixmap;
}

AiAssistantDock::AiAssistantDock(QUndoStack *undoStack, QWidget *parent)
    : QDockWidget(tr("AI Assistant"), parent)
    , m_undoStack(undoStack)
{
    LOG_DEBUG() << "begin";
    setObjectName("AiAssistantDock");
    toggleViewAction()->setIcon(
        QIcon::fromTheme("help-about", QIcon(":/icons/oxygen/32x32/actions/help-about.png")));

    auto content = new QWidget;
    content->setObjectName("aiAssistantContent");
    auto layout = new QVBoxLayout(content);
    layout->setContentsMargins(12, 12, 12, 12);
    layout->setSpacing(10);

    // 1. Is an AI connected?
    auto statusRow = new QHBoxLayout;
    m_statusDot = new QLabel;
    m_statusDot->setObjectName("aiStatusDot");
    statusRow->addWidget(m_statusDot, 0, Qt::AlignTop);
    auto statusText = new QVBoxLayout;
    m_statusLabel = sectionTitle(QString());
    m_statusLabel->setObjectName("aiStatusLabel");
    m_statusDetail = new QLabel;
    m_statusDetail->setObjectName("aiStatusDetail");
    m_statusDetail->setWordWrap(true);
    statusText->addWidget(m_statusLabel);
    statusText->addWidget(m_statusDetail);
    statusRow->addLayout(statusText, 1);
    layout->addLayout(statusRow);

    auto buttons = new QHBoxLayout;
    m_connectButton = new QToolButton;
    m_connectButton->setObjectName("aiConnectButton");
    m_connectButton->setText(tr("Connect to Claude"));
    m_connectButton->setToolTip(
        tr("Adds Shotcut AI to Claude Desktop or Claude Code, without copying anything."));
    m_connectButton->setPopupMode(QToolButton::InstantPopup);
    m_connectButton->setToolButtonStyle(Qt::ToolButtonTextOnly);
    auto connectMenu = new QMenu(m_connectButton);
    connectMenu->addAction(tr("Claude Desktop (app)"), this, &AiAssistantDock::connectClaudeDesktop);
    connectMenu->addAction(tr("Claude Code (terminal)"), this, &AiAssistantDock::connectClaudeCode);
    m_connectButton->setMenu(connectMenu);
    buttons->addWidget(m_connectButton);
    m_enableButton = new QPushButton(tr("Turn On"));
    m_enableButton->setObjectName("aiEnableButton");
    m_enableButton->setToolTip(tr("Let AI apps on this computer use Shotcut AI."));
    connect(m_enableButton, &QPushButton::clicked, this, [this]() {
        emit serverEnabledRequested(true);
    });
    buttons->addWidget(m_enableButton);
    buttons->addStretch();
    layout->addLayout(buttons);

    m_note = new QLabel;
    m_note->setObjectName("aiNote");
    m_note->setWordWrap(true);
    m_note->hide();
    layout->addWidget(m_note);

    // 2. What did the AI change?
    layout->addSpacing(6);
    layout->addWidget(sectionTitle(tr("What the AI changed")));
    m_noSteps = new QLabel(tr("Nothing yet. Every change of the AI appears here, and you can "
                              "undo it with one click."));
    m_noSteps->setWordWrap(true);
    layout->addWidget(m_noSteps);
    m_steps = new QListWidget;
    m_steps->setObjectName("aiStepsList");
    m_steps->setMinimumHeight(90);
    m_steps->setMaximumHeight(170);
    layout->addWidget(m_steps);
    m_undoButton = new QPushButton(tr("Undo This Step"));
    m_undoButton->setObjectName("aiUndoButton");
    m_undoButton->setEnabled(false);
    connect(m_undoButton, &QPushButton::clicked, this, &AiAssistantDock::onUndoClicked);
    connect(m_steps, &QListWidget::currentRowChanged, this, [this]() {
        const auto item = m_steps->currentItem();
        m_undoButton->setEnabled(item);
        if (item) {
            const bool done = item->data(Qt::UserRole).toInt() < m_undoStack->index();
            m_undoButton->setText(done ? tr("Undo This Step") : tr("Redo This Step"));
            m_undoButton->setToolTip(
                done ? tr("Goes back to before this step. Later steps are undone too.")
                     : tr("Applies this step again, and the ones before it."));
        }
    });
    layout->addWidget(m_undoButton, 0, Qt::AlignLeft);

    // 3. What can I ask?
    layout->addSpacing(6);
    layout->addWidget(sectionTitle(tr("What would you like to do?")));
    auto hint = new QLabel(tr("Click a request to copy it, then paste it in the Claude chat "
                              "(Ctrl+V). In Claude Desktop they are also in the + button."));
    hint->setWordWrap(true);
    layout->addWidget(hint);
    for (const auto &recipe : AiTools::recipes())
        layout->addWidget(makeRecipeButton(recipe.title, recipe.description, recipe.text({})));

    auto guide = new QLabel(QStringLiteral("<a href=\"%1\">%2</a>")
                                .arg(guideUrl(), tr("First steps guide (in Spanish)")));
    guide->setOpenExternalLinks(true);
    layout->addSpacing(6);
    layout->addWidget(guide);
    layout->addStretch();

    content->setStyleSheet(QStringLiteral(
        "QLabel#aiRecipeCard { border: 1px solid #2A2E37; border-radius: 8px; padding: 8px 10px; }"
        "QLabel#aiRecipeCard:hover { background-color: #262A33; border-color: #FF7A45; }"
        "QLabel#aiRecipeCard:focus { border-color: #FF7A45; }"
        "QToolButton#aiConnectButton { background-color: #FF7A45; color: #140A05; border: 1px "
        "solid #FF7A45; border-radius: 8px; padding: 6px 14px; font-weight: 600; }"
        "QToolButton#aiConnectButton:hover { background-color: #FF8F61; }"
        "QToolButton#aiConnectButton:pressed { background-color: #E66835; }"
        "QToolButton#aiConnectButton:disabled { background-color: #2A2E37; border-color: "
        "#2A2E37; color: #5F6672; }"));
    Util::followAccentColor(content);

    auto scroll = new QScrollArea;
    scroll->setWidgetResizable(true);
    scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    scroll->setFrameShape(QFrame::NoFrame);
    scroll->setWidget(content);
    setWidget(scroll);

    if (m_undoStack) {
        connect(m_undoStack, &QUndoStack::indexChanged, this, &AiAssistantDock::updateSteps);
        connect(m_undoStack, &QUndoStack::cleanChanged, this, &AiAssistantDock::updateSteps);
    }
    // "Connected" fades to "waiting" when the AI is quiet for a while.
    auto timer = new QTimer(this);
    connect(timer, &QTimer::timeout, this, &AiAssistantDock::updateStatus);
    timer->start(30000);

    updateStatus();
    updateSteps();
    LOG_DEBUG() << "end";
}

QString AiAssistantDock::guideUrl()
{
    return QStringLiteral(
        "https://github.com/Foxlith/Shotcut-AI/blob/master/docs/guia-principiante.md");
}

QWidget *AiAssistantDock::makeRecipeButton(const QString &title,
                                           const QString &description,
                                           const QString &text)
{
    // A card that wraps to the width of the panel: a label that acts as a button.
    auto card = new QLabel(
        QStringLiteral("<b>%1</b><br>%2").arg(title.toHtmlEscaped(), description.toHtmlEscaped()));
    card->setObjectName("aiRecipeCard");
    card->setWordWrap(true);
    card->setToolTip(text);
    card->setCursor(Qt::PointingHandCursor);
    card->setFocusPolicy(Qt::StrongFocus);
    card->setAccessibleName(title);
    card->setProperty("recipeTitle", title);
    card->setProperty("recipeText", text);
    card->installEventFilter(this);
    return card;
}

bool AiAssistantDock::eventFilter(QObject *watched, QEvent *event)
{
    const auto card = qobject_cast<QLabel *>(watched);
    if (card && card->objectName() == QLatin1String("aiRecipeCard")) {
        bool activate = false;
        if (event->type() == QEvent::MouseButtonRelease)
            activate = static_cast<QMouseEvent *>(event)->button() == Qt::LeftButton;
        else if (event->type() == QEvent::KeyPress) {
            const int key = static_cast<QKeyEvent *>(event)->key();
            activate = key == Qt::Key_Return || key == Qt::Key_Enter || key == Qt::Key_Space;
        }
        if (activate) {
            QGuiApplication::clipboard()->setText(card->property("recipeText").toString());
            showNote(tr("Copied \"%1\". Paste it in the Claude chat with Ctrl+V.")
                         .arg(card->property("recipeTitle").toString()));
            return true;
        }
    }
    return QDockWidget::eventFilter(watched, event);
}

void AiAssistantDock::showNote(const QString &text)
{
    m_note->setText(text);
    m_note->show();
}

void AiAssistantDock::setServer(AIAgentServer *server)
{
    if (m_server) {
        m_server->disconnect(this);
        m_server->tools()->disconnect(this);
    }
    m_server = server;
    if (m_server) {
        connect(m_server.data(),
                &AIAgentServer::clientActivity,
                this,
                [this](const QString &name, const QString &) { onClientActivity(name); });
        connect(m_server->tools(), &AiTools::stepDone, this, &AiAssistantDock::onStepDone);
    } else {
        m_lastActivity = QDateTime();
    }
    updateStatus();
}

AiAssistantDock::State AiAssistantDock::state() const
{
    if (!m_server)
        return State::Off;
    if (!m_server->isListening())
        return State::Failed;
    if (m_lastActivity.isValid()
        && m_lastActivity.secsTo(QDateTime::currentDateTime()) < kConnectedSeconds)
        return State::Connected;
    return State::Waiting;
}

QString AiAssistantDock::stateText() const
{
    switch (state()) {
    case State::Off:
        return tr("The AI is off");
    case State::Failed:
        return tr("The AI could not start");
    case State::Waiting:
        return tr("Waiting for the AI");
    case State::Connected:
        return m_clientName.isEmpty() ? tr("Connected to the AI")
                                      : tr("Connected to %1").arg(m_clientName);
    }
    return QString();
}

void AiAssistantDock::onClientActivity(const QString &clientName)
{
    const auto before = state();
    if (!clientName.isEmpty())
        m_clientName = clientName;
    m_lastActivity = QDateTime::currentDateTime();
    if (before != State::Connected)
        updateStatus();
}

void AiAssistantDock::updateStatus()
{
    const auto current = state();
    QColor color;
    QString detail;
    switch (current) {
    case State::Off:
        color = QColor("#7A808C");
        detail = tr("Turn it on so that an AI app (such as Claude) can edit with you.");
        break;
    case State::Failed:
        color = QColor("#E5484D");
        detail = tr("%1. Another program may be using port %2: close it, or change the port, "
                    "and restart Shotcut AI.")
                     .arg(m_server->errorString())
                     .arg(m_server->port());
        break;
    case State::Waiting:
        color = QColor("#F5B83D");
        detail = m_lastActivity.isValid()
                     ? tr("Last seen at %1. Ask something in the Claude chat to continue.")
                           .arg(QLocale().toString(m_lastActivity.time(), QLocale::ShortFormat))
                     : tr("Click Connect to Claude once, then open Claude and ask for something "
                          "from the list below.");
        break;
    case State::Connected:
        color = QColor("#3DD68C");
        detail = tr("The AI can see and edit your project. You can undo any change below.");
        break;
    }
    m_statusDot->setPixmap(dot(color, 14));
    m_statusLabel->setText(stateText());
    m_statusDetail->setText(detail);
    m_enableButton->setVisible(current == State::Off);
    m_connectButton->setEnabled(current != State::Off);
    emit stateChanged();
}

void AiAssistantDock::onStepDone(const QUndoCommand *command)
{
    m_stepTimes.insert(command, QDateTime::currentDateTime());
    onClientActivity(QString());
    updateSteps();
}

void AiAssistantDock::updateSteps()
{
    if (!m_undoStack)
        return;
    const auto prefix = AiTools::stepPrefix();
    const int selected = m_steps->currentItem() ? m_steps->currentItem()->data(Qt::UserRole).toInt()
                                                : -1;
    QHash<const QUndoCommand *, QDateTime> times;
    m_steps->clear();
    for (int i = m_undoStack->count() - 1; i >= 0; --i) {
        const auto command = m_undoStack->command(i);
        if (!command || !command->text().startsWith(prefix))
            continue;
        const bool done = i < m_undoStack->index();
        QString text = command->text().mid(prefix.size());
        const auto time = m_stepTimes.value(command);
        if (time.isValid()) {
            times.insert(command, time);
            text = QLocale().toString(time.time(), QLocale::ShortFormat) + QStringLiteral("  ")
                   + text;
        }
        if (!done)
            text += QLatin1Char(' ') + tr("(undone)");
        auto item = new QListWidgetItem(text, m_steps);
        item->setData(Qt::UserRole, i);
        if (!done)
            item->setForeground(palette().color(QPalette::Disabled, QPalette::Text));
        if (i == selected)
            m_steps->setCurrentItem(item);
    }
    // Forget the steps that left the undo stack.
    m_stepTimes = times;
    m_noSteps->setVisible(m_steps->count() == 0);
    m_steps->setVisible(m_steps->count() > 0);
    m_undoButton->setVisible(m_steps->count() > 0);
    m_undoButton->setEnabled(m_steps->currentItem());
}

void AiAssistantDock::onUndoClicked()
{
    const auto item = m_steps->currentItem();
    if (!item || !m_undoStack)
        return;
    const int index = item->data(Qt::UserRole).toInt();
    const bool done = index < m_undoStack->index();
    // Undo this step and the later ones, or redo up to and including it.
    m_undoStack->setIndex(done ? index : index + 1);
}

void AiAssistantDock::connectClaudeDesktop()
{
    const quint16 port = m_server ? m_server->port() : quint16(Settings.aiServerPort());
#if defined(Q_OS_WIN)
    const auto configDir = qEnvironmentVariable("APPDATA");
    const auto localAppData = qEnvironmentVariable("LOCALAPPDATA");
#elif defined(Q_OS_MAC)
    const auto configDir = QStandardPaths::writableLocation(QStandardPaths::GenericDataLocation);
    const QString localAppData;
#else
    const auto configDir = QStandardPaths::writableLocation(QStandardPaths::GenericConfigLocation);
    const QString localAppData;
#endif
    const auto candidates = ClientSetup::claudeDesktopConfigCandidates(configDir, localAppData);
    const auto path = ClientSetup::chooseConfigFile(candidates);
    const bool installed = QFileInfo(path).dir().exists();
    QString error;
    if (path.isEmpty()
        || !ClientSetup::writeMcpServers(path, AIAgentServer::claudeDesktopServers(port), &error)) {
        LOG_WARNING() << "Cannot connect Claude Desktop:" << error;
        QMessageBox::warning(this,
                             tr("Connect to Claude Desktop"),
                             tr("Shotcut AI could not change the settings of Claude Desktop.\n\n"
                                "%1\n\nUse Settings > AI Agent (MCP) > Copy MCP Configuration "
                                "> Claude Desktop instead.")
                                 .arg(error));
        return;
    }
    LOG_INFO() << "Connected Claude Desktop in" << path;
    QString message = tr("Done! Shotcut AI is now in Claude Desktop.\n\n"
                         "1. Close Claude Desktop completely (also from the icons next to the "
                         "clock) and open it again.\n"
                         "2. In a new chat, click + and choose a request of Shotcut AI, or "
                         "just write what you want to do with your video.");
    if (!installed)
        message += QStringLiteral("\n\n")
                   + tr("Claude Desktop does not seem to be installed yet: get it from "
                        "claude.ai/download. It will find Shotcut AI when it opens.");
    QMessageBox::information(this, tr("Connect to Claude Desktop"), message);
    showNote(tr("Claude Desktop is set up. A copy of its previous settings is in %1.bak.")
                 .arg(QDir::toNativeSeparators(path)));
}

void AiAssistantDock::connectClaudeCode()
{
    const quint16 port = m_server ? m_server->port() : quint16(Settings.aiServerPort());
    const auto commands = AIAgentServer::clientConfiguration(Mcp::Client::ClaudeCode, port);
    const auto claude = QStandardPaths::findExecutable(QStringLiteral("claude"));
    if (claude.isEmpty()) {
        QGuiApplication::clipboard()->setText(commands);
        QMessageBox::information(this,
                                 tr("Connect to Claude Code"),
                                 tr("Claude Code was not found on this computer, so the "
                                    "commands were copied instead. Paste them in a terminal "
                                    "where Claude Code works."));
        return;
    }
    // The same servers as the copied commands, for every folder (user scope).
    QList<QPair<QString, QStringList>> servers{
        {QStringLiteral("shotcut-ai"),
         {QStringLiteral("--transport"),
          QStringLiteral("http"),
          QStringLiteral("shotcut-ai"),
          QStringLiteral("http://127.0.0.1:%1/mcp").arg(port)}}};
    const auto analysis = AIAgentServer::analysisPath();
    if (!analysis.isEmpty())
        servers.append(
            {QStringLiteral("shotcut-analysis"),
             {QStringLiteral("shotcut-analysis"), AIAgentServer::pythonPath(), analysis}});
    QApplication::setOverrideCursor(Qt::WaitCursor);
    QStringList failures;
    for (const auto &server : servers) {
        // Replace an older entry of the same name, if any.
        QProcess::execute(claude, {"mcp", "remove", "--scope", "user", server.first});
        QProcess process;
        process.start(claude, QStringList{"mcp", "add", "--scope", "user"} + server.second);
        if (!process.waitForFinished(30000) || process.exitCode() != 0)
            failures << server.first + QStringLiteral(": ")
                            + QString::fromUtf8(process.readAllStandardError()).trimmed();
    }
    QApplication::restoreOverrideCursor();
    if (failures.isEmpty()) {
        QMessageBox::information(this,
                                 tr("Connect to Claude Code"),
                                 tr("Done! Start Claude Code in a terminal (claude) and ask for "
                                    "what you want to do with your video."));
    } else {
        QGuiApplication::clipboard()->setText(commands);
        QMessageBox::warning(this,
                             tr("Connect to Claude Code"),
                             tr("Claude Code did not accept the setup:\n%1\n\nThe commands were "
                                "copied so you can run them in a terminal.")
                                 .arg(failures.join('\n')));
    }
}
