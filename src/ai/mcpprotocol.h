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

#ifndef MCPPROTOCOL_H
#define MCPPROTOCOL_H

#include <functional>
#include <QByteArray>
#include <QHash>
#include <QJsonArray>
#include <QJsonObject>
#include <QJsonValue>
#include <QList>
#include <QPair>
#include <QString>
#include <QStringList>

/*!
  \namespace Mcp
  \brief The server side of the Model Context Protocol: JSON-RPC 2.0 messages, tools and
  the HTTP pieces of the Streamable HTTP transport.

  It depends only on Qt Core, so it is unit tested without the application
  (tests/test_mcp_protocol.cpp). AIAgentServer carries the messages and AiTools
  registers the tools of Shotcut.
*/
namespace Mcp {

enum ErrorCode {
    ParseError = -32700,
    InvalidRequest = -32600,
    MethodNotFound = -32601,
    InvalidParams = -32602,
    InternalError = -32603,
};

/// The result of a tool call, sent to the client as a CallToolResult.
struct ToolResult
{
    QJsonObject data;        ///< sent to the client once, as compact JSON text
    QString text;            ///< a message for the model, before the data
    QJsonArray extraContent; ///< more content blocks, such as images
    bool isError = false;

    static ToolResult success(const QJsonObject &data, const QString &text = QString());
    /// A tool execution error: the model reads the message and can try again.
    static ToolResult failure(const QString &message);
    QJsonObject toJson() const;
};

struct Tool
{
    QString name;
    QString title;
    QString description;
    QJsonObject inputSchema;
    QJsonObject annotations;
    std::function<ToolResult(const QJsonObject &arguments)> handler;

    /// The tool as listed by tools/list.
    QJsonObject toJson() const;
};

/*!
  \class Mcp::Server
  \brief Answers MCP requests: initialize, ping, tools/list and tools/call.
*/
class Server
{
public:
    Server(const QString &name,
           const QString &title,
           const QString &version,
           const QString &instructions = QString());

    void addTool(const Tool &tool);
    const Tool *tool(const QString &name) const;
    QStringList toolNames() const;

    /// Validates the arguments and calls the tool. Unknown tools and invalid arguments
    /// give an error result.
    ToolResult callTool(const QString &name, const QJsonObject &arguments) const;

    struct Reply
    {
        int httpStatus;
        QByteArray body; ///< JSON; empty for 202 Accepted
    };
    /// Handles the body of an HTTP POST to the MCP endpoint: one JSON-RPC message or a
    /// batch (protocol version 2025-03-26).
    Reply handlePost(const QByteArray &body) const;

    /// Handles one JSON-RPC message. Returns false when it needs no response
    /// (a notification or a response from the client).
    bool handleMessage(const QJsonObject &message, QJsonObject &response) const;

    /// The protocol versions this server speaks, the latest first.
    static QStringList protocolVersions();
    /// The requested version if it is supported, else the latest one.
    static QString negotiateVersion(const QString &requested);
    /// Checks arguments against a JSON schema (type, required, properties,
    /// additionalProperties, enum, minimum, maximum, items and minItems). Returns an
    /// empty string when they are valid, else an explanation for the model.
    static QString validateArguments(const QJsonObject &schema, const QJsonObject &arguments);
    static QJsonObject errorResponse(const QJsonValue &id, int code, const QString &message);

private:
    QJsonObject initializeResult(const QJsonObject &params) const;

    QString m_name;
    QString m_title;
    QString m_version;
    QString m_instructions;
    QList<Tool> m_tools;
    QHash<QString, int> m_toolIndex;
};

/// An HTTP/1.1 request, as far as the MCP endpoint needs it.
struct HttpRequest
{
    QByteArray method;
    QByteArray target;
    QHash<QByteArray, QByteArray> headers; ///< names in lower case
    QByteArray body;

    QByteArray header(const QByteArray &name) const;
    /// The target without the query string.
    QByteArray path() const;
    bool isWebSocketUpgrade() const;
};

enum class ParseResult { Incomplete, Complete, Invalid, TooLarge };

/// Whether \a data holds the whole header section of a request.
bool hasCompleteHeaders(const QByteArray &data);
/// Parses a request with a Content-Length or chunked body. \a consumed receives the number
/// of bytes of \a data that the request used.
ParseResult parseHttpRequest(const QByteArray &data,
                             HttpRequest &request,
                             qsizetype maxBodySize = 8 * 1024 * 1024,
                             qsizetype *consumed = nullptr);
/// Whether an Origin header comes from this computer: absent, or http(s) with the host
/// localhost, 127.0.0.1 or [::1] (any port). Web pages elsewhere are refused, as the MCP
/// specification requires against DNS rebinding.
bool isLocalOrigin(const QByteArray &origin);
/// Whether a Host header names this computer (absent, localhost, 127.0.0.1 or [::1]).
bool isLocalHost(const QByteArray &host);
QByteArray reasonPhrase(int status);

/// The AI clients whose configuration Shotcut AI can copy.
enum class Client { ClaudeCode, ClaudeDesktop, OpenCode, Antigravity };
/// What to paste in the configuration of an AI client: commands for Claude Code, JSON with
/// the HTTP endpoint for OpenCode, and JSON that starts the stdio bridge with \a python for
/// Claude Desktop and Antigravity. Each one also starts the media analysis server at
/// \a analysisPath with \a python, unless it is empty.
QString clientConfiguration(Client client,
                            quint16 port,
                            const QString &bridgePath,
                            const QString &analysisPath,
                            const QString &python);
/// Apps from the Microsoft Store (MSIX), such as Claude Desktop, save the files that they
/// write under AppData in their package folder
/// (<localAppData>/Packages/<package>/LocalCache/Roaming or Local), where other programs do
/// not look. Returns that copy of \a path when \a path does not exist and a package has it
/// (Claude packages first), else \a path.
QString unvirtualizedPath(const QString &path,
                          const QString &roamingAppData,
                          const QString &localAppData);
/// A complete response that closes the connection.
QByteArray httpResponse(int status,
                        const QByteArray &contentType = QByteArray(),
                        const QByteArray &body = QByteArray(),
                        const QList<QPair<QByteArray, QByteArray>> &headers = {});

} // namespace Mcp

#endif // MCPPROTOCOL_H
