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

#ifndef AITOOLS_H
#define AITOOLS_H

#include "ai/mcpprotocol.h"

#include <functional>
#include <QList>
#include <QObject>

class QUndoCommand;

/*!
  \class AiTools
  \brief The tools of the AI agent server (MCP and WebSocket).

  They read and change the open project through the same code as the user interface,
  so every change is visible at once. Each call that edits is one undo step named
  "AI: ..." and is announced in the status bar of the viewer. A call made while another
  one waits (for example for a dialog) is refused instead of running inside it.
*/
class AiTools : public QObject
{
    Q_OBJECT
public:
    /// A ready-made request for a common job, for people who do not edit video: an MCP
    /// prompt, and a card of the AI Assistant panel that copies the same text.
    struct Recipe
    {
        QString name;
        QString title;
        QString description;
        QList<Mcp::PromptArgument> arguments;
        /// The request, from the arguments; without them it still reads well.
        std::function<QString(const QJsonObject &arguments)> text;
    };

    explicit AiTools(QObject *parent = nullptr);
    void registerTools(Mcp::Server &server);
    void registerPrompts(Mcp::Server &server);

    /// The recipes, in the language of the user interface.
    static QList<Recipe> recipes();
    /// What the server tells the AI about Shotcut AI and about its user.
    static QString instructions();
    /// The prefix of the undo steps of the AI ("AI: ").
    static QString stepPrefix();

signals:
    /// An edit of the AI became the undo step \a command.
    void stepDone(const QUndoCommand *command);

private:
    /// Runs \a body unless another call is running.
    Mcp::ToolResult run(const std::function<Mcp::ToolResult()> &body);
    /// Like run(), as one undo step named "AI: \a title" (dropped when nothing changed).
    Mcp::ToolResult edit(const QString &title, const std::function<Mcp::ToolResult()> &body);

    bool m_busy{false};
};

#endif // AITOOLS_H
