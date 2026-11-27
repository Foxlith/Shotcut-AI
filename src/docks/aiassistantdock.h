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

#ifndef AIASSISTANTDOCK_H
#define AIASSISTANTDOCK_H

#include <QDateTime>
#include <QDockWidget>
#include <QHash>
#include <QPointer>

class AIAgentServer;
class QLabel;
class QListWidget;
class QPushButton;
class QToolButton;
class QUndoCommand;
class QUndoStack;

/*!
  \class AiAssistantDock
  \brief The AI Assistant panel, for people who do not edit video: whether an AI is
  connected (and a button that connects Claude in one click), ready-made requests to copy
  into the chat, and the list of what the AI changed, each step undoable with one click.
*/
class AiAssistantDock : public QDockWidget
{
    Q_OBJECT
public:
    enum class State { Off, Failed, Waiting, Connected };

    explicit AiAssistantDock(QUndoStack *undoStack, QWidget *parent = nullptr);

    /// The running server, or nullptr when it is off.
    void setServer(AIAgentServer *server);
    State state() const;
    /// The text of the status: "Connected to Claude", "Waiting for the AI"...
    QString stateText() const;
    /// The web page of the first steps guide.
    static QString guideUrl();

protected:
    bool eventFilter(QObject *watched, QEvent *event) override;

signals:
    /// The user asked to turn the AI agent server on or off.
    void serverEnabledRequested(bool enabled);
    void stateChanged();

public slots:
    void connectClaudeDesktop();
    void connectClaudeCode();

private slots:
    void onClientActivity(const QString &clientName);
    void onStepDone(const QUndoCommand *command);
    void updateStatus();
    void updateSteps();
    void onUndoClicked();

private:
    QWidget *makeRecipeButton(const QString &title, const QString &description, const QString &text);
    void showNote(const QString &text);

    QUndoStack *m_undoStack;
    QPointer<AIAgentServer> m_server;
    QString m_clientName;
    QDateTime m_lastActivity;
    QHash<const QUndoCommand *, QDateTime> m_stepTimes;
    QLabel *m_statusDot;
    QLabel *m_statusLabel;
    QLabel *m_statusDetail;
    QToolButton *m_connectButton;
    QPushButton *m_enableButton;
    QLabel *m_note;
    QListWidget *m_steps;
    QLabel *m_noSteps;
    QPushButton *m_undoButton;
};

#endif // AIASSISTANTDOCK_H
