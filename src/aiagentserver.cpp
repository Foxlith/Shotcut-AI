#include "aiagentserver.h"
#include "mainwindow.h"
#include <QDebug>
#include <QJsonDocument>
#include <QJsonObject>

AIAgentServer::AIAgentServer(quint16 port, QObject *parent)
    : QObject(parent)
    , m_pWebSocketServer(new QWebSocketServer(QStringLiteral("Shotcut AI Agent Server"),
                                              QWebSocketServer::NonSecureMode,
                                              this))
{
    if (m_pWebSocketServer->listen(QHostAddress::Any, port)) {
        qDebug() << "AI Agent Server successfully listening on port" << port;
        connect(m_pWebSocketServer,
                &QWebSocketServer::newConnection,
                this,
                &AIAgentServer::onNewConnection);
        connect(m_pWebSocketServer, &QWebSocketServer::closed, this, &AIAgentServer::closed);
    } else {
        qDebug() << "Failed to start AI Agent Server on port" << port;
    }
}

AIAgentServer::~AIAgentServer()
{
    m_pWebSocketServer->close();
    qDeleteAll(m_clients.begin(), m_clients.end());
}

void AIAgentServer::onNewConnection()
{
    QWebSocket *pSocket = m_pWebSocketServer->nextPendingConnection();
    qDebug() << "AI Agent Client connected:" << pSocket->peerAddress().toString();

    connect(pSocket, &QWebSocket::textMessageReceived, this, &AIAgentServer::processTextMessage);
    connect(pSocket, &QWebSocket::disconnected, this, &AIAgentServer::socketDisconnected);

    m_clients << pSocket;
    pSocket->sendTextMessage(QStringLiteral(
        "{\"status\":\"connected\", \"message\":\"Welcome to Shotcut AI Edition!\"}"));
}

void AIAgentServer::processTextMessage(QString message)
{
    QWebSocket *pClient = qobject_cast<QWebSocket *>(sender());
    qDebug() << "Message received from AI Agent:" << message;

    QJsonDocument doc = QJsonDocument::fromJson(message.toUtf8());
    if (doc.isNull() || !doc.isObject()) {
        if (pClient) {
            pClient->sendTextMessage(QStringLiteral("{\"error\":\"Invalid JSON\"}"));
        }
        return;
    }

    QJsonObject obj = doc.object();
    QString command = obj["command"].toString();

    // Send feedback to client
    if (pClient) {
        QString response = QStringLiteral("{\"status\":\"success\", \"command_received\":\"")
                           + command + QStringLiteral("\"}");
        pClient->sendTextMessage(response);
    }

    // Execute logic based on command
    // TODO: Connect this to MainWindow timeline actions.
    if (command == "play") {
        qDebug() << "Executing PLAY command via AI Agent!";
        // MAIN.player()->play();
    } else if (command == "pause") {
        qDebug() << "Executing PAUSE command via AI Agent!";
        // MAIN.player()->pause();
    }
}

void AIAgentServer::socketDisconnected()
{
    QWebSocket *pClient = qobject_cast<QWebSocket *>(sender());
    qDebug() << "AI Agent Client disconnected:" << pClient;
    if (pClient) {
        m_clients.removeAll(pClient);
        pClient->deleteLater();
    }
}
