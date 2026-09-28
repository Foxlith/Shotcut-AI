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

#include "aiagentserver.h"

#include "Logger.h"
#include "ai/aitools.h"
#include "qmltypes/qmlapplication.h"

#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPointer>
#include <QTcpServer>
#include <QTcpSocket>
#include <QTimer>
#include <QtWebSockets/QWebSocket>
#include <QtWebSockets/QWebSocketCorsAuthenticator>
#include <QtWebSockets/QWebSocketServer>

static const qsizetype kMaxBodySize = 8 * 1024 * 1024;
static const int kIdleTimeoutMs = 15000;

static const char *kInstructions
    = "Shotcut AI is a video editor that is open on this computer: every tool acts on it "
      "live and the user sees the result at once. Start with get_state, then get_timeline "
      "or get_playlist. Times are seconds (or a timecode such as 00:01:02.500). Tracks are "
      "0-based indices from the top of the timeline, or names such as \"V1\" or \"A1\"; "
      "clips are 0-based indices within their track from get_timeline, or their uuid. Each "
      "edit is one undoable step named \"AI: ...\" (the undo tool reverts it). Use get_frame "
      "to look at the video after a change, and list_actions with run_action for anything "
      "else that Shotcut can do.";

AIAgentServer::AIAgentServer(quint16 port, QObject *parent)
    : QObject(parent)
    , m_port(port)
    , m_webSocketServer(new QWebSocketServer(QStringLiteral("Shotcut AI Agent Server"),
                                             QWebSocketServer::NonSecureMode,
                                             this))
    , m_mcp(QStringLiteral("shotcut-ai"),
            QStringLiteral("Shotcut AI"),
            QCoreApplication::applicationVersion(),
            QString::fromLatin1(kInstructions))
    , m_tools(new AiTools(this))
{
    m_tools->registerTools(m_mcp);

    // The WebSocket server does not listen itself: the TCP servers below hand it the
    // connections that ask for a WebSocket.
    connect(m_webSocketServer,
            &QWebSocketServer::newConnection,
            this,
            &AIAgentServer::onWebSocketConnection);
    connect(m_webSocketServer,
            &QWebSocketServer::originAuthenticationRequired,
            this,
            &AIAgentServer::onOriginAuthenticationRequired);

    // Only this computer: IPv4 and IPv6 loopback, never all network interfaces.
    for (const auto &address :
         {QHostAddress(QHostAddress::LocalHost), QHostAddress(QHostAddress::LocalHostIPv6)}) {
        auto server = new QTcpServer(this);
        if (server->listen(address, port)) {
            connect(server, &QTcpServer::newConnection, this, &AIAgentServer::onNewTcpConnection);
            m_tcpServers << server;
        } else {
            // Without IPv6 on this computer only the IPv4 loopback is used.
            if (address == QHostAddress::LocalHost) {
                m_errorString = server->errorString();
                LOG_WARNING() << "AI Agent Server cannot listen on" << address.toString() << port
                              << server->errorString();
            } else {
                LOG_DEBUG() << "AI Agent Server cannot listen on" << address.toString() << port
                            << server->errorString();
            }
            delete server;
        }
    }
    if (isListening())
        LOG_INFO() << "AI Agent Server listening on" << mcpUrl();
    else
        LOG_WARNING() << "Failed to start AI Agent Server on port" << port << m_errorString;
}

AIAgentServer::~AIAgentServer()
{
    for (auto server : m_tcpServers)
        server->close();
    m_webSocketServer->close();
    qDeleteAll(m_clients.begin(), m_clients.end());
}

bool AIAgentServer::isListening() const
{
    // The IPv4 loopback is the one that the documented URL uses.
    for (auto server : m_tcpServers)
        if (server->serverAddress() == QHostAddress(QHostAddress::LocalHost))
            return true;
    return false;
}

QString AIAgentServer::mcpUrl() const
{
    return QStringLiteral("http://127.0.0.1:%1/mcp").arg(m_port);
}

QString AIAgentServer::toolForCommand(const QString &command)
{
    // The commands that the first version of the WebSocket documented.
    if (command == QLatin1String("open"))
        return QStringLiteral("open_media");
    if (command == QLatin1String("stop"))
        return QStringLiteral("pause");
    return command;
}

QString AIAgentServer::bridgePath()
{
    return QDir::toNativeSeparators(
        QmlApplication::dataDir().absoluteFilePath("shotcut/mcp/shotcut_mcp_bridge.py"));
}

QString AIAgentServer::analysisPath()
{
    const auto path = QmlApplication::dataDir().absoluteFilePath("shotcut/mcp/shotcut_analysis.py");
    return QFileInfo::exists(path) ? QDir::toNativeSeparators(path) : QString();
}

QString AIAgentServer::clientConfiguration(Mcp::Client client, quint16 port)
{
#if defined(Q_OS_WIN)
    const auto python = QStringLiteral("python");
#else
    const auto python = QStringLiteral("python3");
#endif
    return Mcp::clientConfiguration(client, port, bridgePath(), analysisPath(), python);
}

void AIAgentServer::onNewTcpConnection()
{
    auto server = qobject_cast<QTcpServer *>(sender());
    if (!server)
        return;
    while (server->hasPendingConnections()) {
        QTcpSocket *socket = server->nextPendingConnection();
        if (!socket->peerAddress().isLoopback()) {
            socket->abort();
            socket->deleteLater();
            continue;
        }
        m_pending.insert(socket, PendingConnection());
        connect(socket, &QTcpSocket::readyRead, this, [this, socket]() { onTcpReadyRead(socket); });
        connect(socket, &QTcpSocket::disconnected, this, [this, socket]() {
            m_pending.remove(socket);
            socket->deleteLater();
        });
        QPointer<QTcpSocket> guard(socket);
        QTimer::singleShot(kIdleTimeoutMs, this, [this, guard]() {
            if (guard && m_pending.contains(guard.data()))
                guard->abort();
        });
    }
}

void AIAgentServer::onTcpReadyRead(QTcpSocket *socket)
{
    if (!m_pending.contains(socket))
        return;
    auto &pending = m_pending[socket];
    if (!pending.isHttp) {
        // Peek at the headers so that a WebSocket handshake stays unread for QWebSocketServer.
        const QByteArray head = socket->peek(qMin<qint64>(socket->bytesAvailable(), 65536));
        if (!Mcp::hasCompleteHeaders(head)) {
            if (head.size() >= 65536)
                sendAndClose(socket, Mcp::httpResponse(431, "text/plain", "Headers too large"));
            return;
        }
        Mcp::HttpRequest request;
        if (Mcp::parseHttpRequest(head, request, kMaxBodySize) == Mcp::ParseResult::Invalid) {
            sendAndClose(socket, Mcp::httpResponse(400, "text/plain", "Bad request"));
            return;
        }
        if (request.isWebSocketUpgrade()) {
            if (!Mcp::isLocalHost(request.header("host"))
                || !Mcp::isLocalOrigin(request.header("origin"))) {
                LOG_WARNING() << "AI Agent Server refused a WebSocket from"
                              << request.header("origin") << request.header("host");
                sendAndClose(socket, Mcp::httpResponse(403, "text/plain", "Forbidden"));
                return;
            }
            m_pending.remove(socket);
            socket->disconnect(this);
            m_webSocketServer->handleConnection(socket);
            return;
        }
        pending.isHttp = true;
    }

    pending.buffer += socket->readAll();
    Mcp::HttpRequest request;
    switch (Mcp::parseHttpRequest(pending.buffer, request, kMaxBodySize)) {
    case Mcp::ParseResult::Incomplete:
        if (!pending.continueSent && request.header("expect").toLower().contains("100-continue")) {
            pending.continueSent = true;
            socket->write("HTTP/1.1 100 Continue\r\n\r\n");
        }
        return;
    case Mcp::ParseResult::TooLarge:
        sendAndClose(socket, Mcp::httpResponse(413, "text/plain", "Payload too large"));
        return;
    case Mcp::ParseResult::Invalid:
        sendAndClose(socket, Mcp::httpResponse(400, "text/plain", "Bad request"));
        return;
    case Mcp::ParseResult::Complete:
        m_pending.remove(socket);
        respondHttp(socket, request);
        return;
    }
}

void AIAgentServer::respondHttp(QTcpSocket *socket, const Mcp::HttpRequest &request)
{
    auto errorBody = [](const QString &message) {
        return QJsonDocument(
                   Mcp::Server::errorResponse(QJsonValue::Null, Mcp::InvalidRequest, message))
            .toJson(QJsonDocument::Compact);
    };
    // Web pages must not reach this server, also through DNS rebinding.
    if (!Mcp::isLocalHost(request.header("host")) || !Mcp::isLocalOrigin(request.header("origin"))) {
        LOG_WARNING() << "AI Agent Server refused a request from" << request.header("origin")
                      << request.header("host");
        sendAndClose(socket,
                     Mcp::httpResponse(403,
                                       "application/json",
                                       errorBody("Forbidden: only programs on this computer can "
                                                 "use the Shotcut AI server.")));
        return;
    }
    if (request.path() != "/mcp") {
        sendAndClose(socket,
                     Mcp::httpResponse(404,
                                       "text/plain; charset=utf-8",
                                       "Shotcut AI: the MCP endpoint is /mcp.\n"));
        return;
    }
    if (request.method != "POST") {
        // No server-sent event stream (GET) and no sessions to delete (DELETE).
        sendAndClose(socket,
                     Mcp::httpResponse(405,
                                       "text/plain",
                                       "Method not allowed\n",
                                       {{"Allow", "POST"}}));
        return;
    }
    const auto contentType = request.header("content-type").toLower();
    if (!contentType.isEmpty() && !contentType.contains("application/json")) {
        sendAndClose(socket,
                     Mcp::httpResponse(415,
                                       "application/json",
                                       errorBody("Content-Type must be application/json")));
        return;
    }

    // A tool can open a dialog and run a nested event loop, during which the client may
    // disconnect and the socket be deleted.
    QPointer<QTcpSocket> guard(socket);
    const auto reply = m_mcp.handlePost(request.body);
    if (!guard)
        return;
    sendAndClose(socket,
                 Mcp::httpResponse(reply.httpStatus,
                                   reply.body.isEmpty() ? QByteArray() : "application/json",
                                   reply.body));
}

void AIAgentServer::sendAndClose(QTcpSocket *socket, const QByteArray &response)
{
    m_pending.remove(socket);
    socket->write(response);
    // Waits for the data to be written before closing.
    socket->disconnectFromHost();
}

void AIAgentServer::onOriginAuthenticationRequired(QWebSocketCorsAuthenticator *authenticator)
{
    authenticator->setAllowed(Mcp::isLocalOrigin(authenticator->origin().toLatin1()));
}

void AIAgentServer::onWebSocketConnection()
{
    while (m_webSocketServer->hasPendingConnections()) {
        QWebSocket *socket = m_webSocketServer->nextPendingConnection();
        LOG_DEBUG() << "AI Agent Client connected:" << socket->peerAddress().toString();
        connect(socket, &QWebSocket::textMessageReceived, this, &AIAgentServer::processTextMessage);
        connect(socket, &QWebSocket::disconnected, this, &AIAgentServer::socketDisconnected);
        m_clients << socket;
        QJsonArray commands;
        for (const auto &name : m_mcp.toolNames())
            commands.append(name);
        const QJsonObject welcome{{"status", "connected"},
                                  {"message", "Welcome to Shotcut AI Edition!"},
                                  {"mcp", mcpUrl()},
                                  {"commands", commands}};
        socket->sendTextMessage(
            QString::fromUtf8(QJsonDocument(welcome).toJson(QJsonDocument::Compact)));
    }
}

QString AIAgentServer::handleWebSocketMessage(const QString &message)
{
    auto reply = [](const QJsonObject &object) {
        return QString::fromUtf8(QJsonDocument(object).toJson(QJsonDocument::Compact));
    };
    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(message.toUtf8(), &error);
    if (error.error != QJsonParseError::NoError || (!document.isObject() && !document.isArray()))
        return reply({{"status", "error"}, {"error", "Invalid JSON"}});

    // JSON-RPC (MCP) messages work on the WebSocket too.
    const auto object = document.object();
    if (document.isArray() || object.contains("jsonrpc") || object.contains("method"))
        return QString::fromUtf8(m_mcp.handlePost(message.toUtf8()).body);

    // {"command": "play"} or {"command": "seek", "seconds": 5} or
    // {"command": "seek", "arguments": {"seconds": 5}}
    const QString command = object.value("command").toString();
    if (command.isEmpty())
        return reply({{"status", "error"}, {"error", "Missing \"command\""}});
    const QString toolName = toolForCommand(command);
    if (!m_mcp.tool(toolName)) {
        QJsonArray commands;
        for (const auto &name : m_mcp.toolNames())
            commands.append(name);
        return reply({{"status", "error"},
                      {"command_received", command},
                      {"error", QStringLiteral("Unknown command: %1").arg(command)},
                      {"available_commands", commands}});
    }
    QJsonObject arguments;
    if (object.value("arguments").isObject()) {
        arguments = object.value("arguments").toObject();
    } else {
        arguments = object;
        arguments.remove("command");
    }
    const auto result = m_mcp.callTool(toolName, arguments);
    if (result.isError)
        return reply({{"status", "error"}, {"command_received", command}, {"error", result.text}});
    QJsonObject response{{"status", "success"}, {"command_received", command}};
    if (!result.data.isEmpty())
        response["result"] = result.data;
    else if (!result.text.isEmpty())
        response["message"] = result.text;
    return reply(response);
}

void AIAgentServer::processTextMessage(const QString &message)
{
    QPointer<QWebSocket> client = qobject_cast<QWebSocket *>(sender());
    LOG_DEBUG() << "Message received from AI Agent:" << message.left(200);
    const auto response = handleWebSocketMessage(message);
    if (client && !response.isEmpty())
        client->sendTextMessage(response);
}

void AIAgentServer::socketDisconnected()
{
    QWebSocket *client = qobject_cast<QWebSocket *>(sender());
    LOG_DEBUG() << "AI Agent Client disconnected:" << client;
    if (client) {
        m_clients.removeAll(client);
        client->deleteLater();
    }
}
