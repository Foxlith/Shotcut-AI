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

#ifndef AIAGENTSERVER_H
#define AIAGENTSERVER_H

#include "ai/mcpprotocol.h"

#include <QHash>
#include <QList>
#include <QObject>

class AiTools;
class QTcpServer;
class QTcpSocket;
class QWebSocket;
class QWebSocketCorsAuthenticator;
class QWebSocketServer;

/*!
  \class AIAgentServer
  \brief The live AI agent server: MCP (Streamable HTTP) at http://127.0.0.1:<port>/mcp
  and the JSON WebSocket at ws://127.0.0.1:<port>, both on the same port.

  It listens only on 127.0.0.1 and ::1 and refuses requests from web pages (Origin and
  Host headers), so only programs on this computer can drive Shotcut AI. The tools come
  from AiTools and run on the GUI thread, so they change the open project live.
*/
class AIAgentServer : public QObject
{
    Q_OBJECT
public:
    explicit AIAgentServer(quint16 port, QObject *parent = nullptr);
    virtual ~AIAgentServer();

    bool isListening() const;
    quint16 port() const { return m_port; }
    QString errorString() const { return m_errorString; }
    QString mcpUrl() const;
    const Mcp::Server &mcp() const { return m_mcp; }

    /// The tool that runs a command of the JSON WebSocket ({"command": "play", ...}).
    static QString toolForCommand(const QString &command);

    /// The installed stdio bridge for clients that only start local processes.
    static QString bridgePath();
    /// What to paste in the configuration of an AI client to connect it to Shotcut AI.
    static QString clientConfiguration(Mcp::Client client, quint16 port);

signals:
    void closed();

private slots:
    void onNewTcpConnection();
    void onWebSocketConnection();
    void processTextMessage(const QString &message);
    void socketDisconnected();
    void onOriginAuthenticationRequired(QWebSocketCorsAuthenticator *authenticator);

private:
    struct PendingConnection
    {
        QByteArray buffer;
        bool isHttp = false;
        bool continueSent = false;
    };

    void onTcpReadyRead(QTcpSocket *socket);
    void respondHttp(QTcpSocket *socket, const Mcp::HttpRequest &request);
    void sendAndClose(QTcpSocket *socket, const QByteArray &response);
    QString handleWebSocketMessage(const QString &message);

    quint16 m_port;
    QList<QTcpServer *> m_tcpServers;
    QWebSocketServer *m_webSocketServer;
    QList<QWebSocket *> m_clients;
    QHash<QTcpSocket *, PendingConnection> m_pending;
    Mcp::Server m_mcp;
    AiTools *m_tools;
    QString m_errorString;
};

#endif // AIAGENTSERVER_H
