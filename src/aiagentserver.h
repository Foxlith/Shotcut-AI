#ifndef AIAGENTSERVER_H
#define AIAGENTSERVER_H

#include <QList>
#include <QObject>
#include <QtWebSockets/QWebSocket>
#include <QtWebSockets/QWebSocketServer>

class AIAgentServer : public QObject
{
    Q_OBJECT
public:
    explicit AIAgentServer(quint16 port, QObject *parent = nullptr);
    virtual ~AIAgentServer();

Q_SIGNALS:
    void closed();

private Q_SLOTS:
    void onNewConnection();
    void processTextMessage(QString message);
    void socketDisconnected();

private:
    QWebSocketServer *m_pWebSocketServer;
    QList<QWebSocket *> m_clients;
};

#endif // AIAGENTSERVER_H
