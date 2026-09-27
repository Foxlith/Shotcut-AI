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

#include "ai/mcpprotocol.h"

#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QtTest>

class TestMcpProtocol : public QObject
{
    Q_OBJECT

private:
    static QJsonObject parse(const QByteArray &json)
    {
        return QJsonDocument::fromJson(json).object();
    }

    static QByteArray request(int id, const QString &method, const QJsonObject &params = {})
    {
        QJsonObject message{{"jsonrpc", "2.0"}, {"id", id}, {"method", method}};
        if (!params.isEmpty())
            message["params"] = params;
        return QJsonDocument(message).toJson(QJsonDocument::Compact);
    }

    /// A server with a "seek" tool that records its arguments.
    static Mcp::Server *makeServer(QJsonObject *received)
    {
        auto server
            = new Mcp::Server("shotcut-ai", "Shotcut AI", "26.9.27", "Call get_state first.");
        Mcp::Tool seek;
        seek.name = "seek";
        seek.title = "Seek";
        seek.description = "Moves the playhead.";
        seek.inputSchema = parse(R"({"type": "object",
            "properties": {"seconds": {"type": "number", "minimum": 0},
                           "frames": {"type": "integer"},
                           "target": {"type": "string", "enum": ["source", "project"]},
                           "clips": {"type": "array", "minItems": 1,
                                     "items": {"type": "object",
                                               "properties": {"track": {"type": "integer"}},
                                               "required": ["track"]}}},
            "required": ["seconds"], "additionalProperties": false})");
        seek.annotations = QJsonObject{{"idempotentHint", true}};
        seek.handler = [received](const QJsonObject &arguments) {
            *received = arguments;
            return Mcp::ToolResult::success(QJsonObject{{"position", arguments.value("seconds")}});
        };
        server->addTool(seek);
        return server;
    }

private slots:
    void initializeNegotiatesTheVersion()
    {
        QJsonObject received;
        QScopedPointer<Mcp::Server> server(makeServer(&received));
        for (const auto &version : Mcp::Server::protocolVersions()) {
            const auto reply = server->handlePost(
                request(1, "initialize", {{"protocolVersion", version}}));
            QCOMPARE(reply.httpStatus, 200);
            const auto result = parse(reply.body).value("result").toObject();
            QCOMPARE(result.value("protocolVersion").toString(), version);
        }
        const auto reply = server->handlePost(
            request(2, "initialize", {{"protocolVersion", "1999-01-01"}}));
        const auto response = parse(reply.body);
        QCOMPARE(response.value("id").toInt(), 2);
        const auto result = response.value("result").toObject();
        QCOMPARE(result.value("protocolVersion").toString(), QString("2025-11-25"));
        QVERIFY(result.value("capabilities").toObject().contains("tools"));
        QCOMPARE(result.value("serverInfo").toObject().value("name").toString(),
                 QString("shotcut-ai"));
        QCOMPARE(result.value("serverInfo").toObject().value("version").toString(),
                 QString("26.9.27"));
        QCOMPARE(result.value("instructions").toString(), QString("Call get_state first."));
    }

    void notificationsAreAccepted()
    {
        QJsonObject received;
        QScopedPointer<Mcp::Server> server(makeServer(&received));
        const auto reply = server->handlePost(
            R"({"jsonrpc": "2.0", "method": "notifications/initialized"})");
        QCOMPARE(reply.httpStatus, 202);
        QVERIFY(reply.body.isEmpty());
        // A response from the client needs no answer either.
        QCOMPARE(server->handlePost(R"({"jsonrpc": "2.0", "id": 7, "result": {}})").httpStatus, 202);
    }

    void pingAndLists()
    {
        QJsonObject received;
        QScopedPointer<Mcp::Server> server(makeServer(&received));
        auto response = parse(server->handlePost(request(3, "ping")).body);
        QVERIFY(response.value("result").isObject());
        QVERIFY(response.value("result").toObject().isEmpty());

        response = parse(server->handlePost(request(4, "tools/list")).body);
        const auto tools = response.value("result").toObject().value("tools").toArray();
        QCOMPARE(tools.size(), 1);
        const auto tool = tools.first().toObject();
        QCOMPARE(tool.value("name").toString(), QString("seek"));
        QCOMPARE(tool.value("title").toString(), QString("Seek"));
        QCOMPARE(tool.value("inputSchema").toObject().value("type").toString(), QString("object"));
        QVERIFY(tool.value("annotations").toObject().value("idempotentHint").toBool());

        response = parse(server->handlePost(request(5, "prompts/list")).body);
        QVERIFY(response.value("result").toObject().value("prompts").isArray());
    }

    void callsATool()
    {
        QJsonObject received;
        QScopedPointer<Mcp::Server> server(makeServer(&received));
        const auto reply = server->handlePost(
            request(6,
                    "tools/call",
                    {{"name", "seek"},
                     {"arguments", QJsonObject{{"seconds", 2.5}, {"target", "project"}}}}));
        QCOMPARE(reply.httpStatus, 200);
        QCOMPARE(received.value("seconds").toDouble(), 2.5);
        const auto result = parse(reply.body).value("result").toObject();
        QCOMPARE(result.value("isError").toBool(), false);
        QCOMPARE(result.value("structuredContent").toObject().value("position").toDouble(), 2.5);
        const auto text = result.value("content").toArray().first().toObject();
        QCOMPARE(text.value("type").toString(), QString("text"));
        QCOMPARE(parse(text.value("text").toString().toUtf8()).value("position").toDouble(), 2.5);
    }

    void invalidArgumentsAreToolErrors_data()
    {
        QTest::addColumn<QString>("arguments");
        QTest::addColumn<QString>("expected");
        QTest::newRow("missing") << "{}"
                                 << "missing required argument \"seconds\"";
        QTest::newRow("type") << R"({"seconds": "two"})"
                              << "\"seconds\" must be number, not string";
        QTest::newRow("minimum") << R"({"seconds": -1})"
                                 << "\"seconds\" must be at least 0";
        QTest::newRow("integer") << R"({"seconds": 1, "frames": 2.5})"
                                 << "\"frames\" must be integer";
        QTest::newRow("enum") << R"({"seconds": 1, "target": "timeline"})"
                              << "\"target\" must be one of \"source\", \"project\"";
        QTest::newRow("unknown") << R"({"seconds": 1, "second": 1})"
                                 << "unknown argument \"second\"";
        QTest::newRow("minItems") << R"({"seconds": 1, "clips": []})"
                                  << "at least 1 item";
        QTest::newRow("nested") << R"({"seconds": 1, "clips": [{"clip": 0}]})"
                                << "missing required argument \"\"clips\"[0].track\"";
    }

    void invalidArgumentsAreToolErrors()
    {
        QFETCH(QString, arguments);
        QFETCH(QString, expected);
        QJsonObject received{{"untouched", true}};
        QScopedPointer<Mcp::Server> server(makeServer(&received));
        const auto reply = server->handlePost(
            request(8,
                    "tools/call",
                    {{"name", "seek"},
                     {"arguments", QJsonDocument::fromJson(arguments.toUtf8()).object()}}));
        QCOMPARE(reply.httpStatus, 200);
        const auto result = parse(reply.body).value("result").toObject();
        QVERIFY(result.value("isError").toBool());
        const auto message
            = result.value("content").toArray().first().toObject().value("text").toString();
        QVERIFY2(message.contains(expected), qPrintable(message));
        // The handler never ran.
        QVERIFY(received.value("untouched").toBool());
    }

    void protocolErrors()
    {
        QJsonObject received;
        QScopedPointer<Mcp::Server> server(makeServer(&received));
        auto reply = server->handlePost(request(9, "tools/call", {{"name", "nope"}}));
        auto error = parse(reply.body).value("error").toObject();
        QCOMPARE(error.value("code").toInt(), int(Mcp::InvalidParams));
        QVERIFY(error.value("message").toString().contains("nope"));

        reply = server->handlePost(request(10, "sampling/createMessage"));
        QCOMPARE(parse(reply.body).value("error").toObject().value("code").toInt(),
                 int(Mcp::MethodNotFound));

        reply = server->handlePost("{not json");
        QCOMPARE(reply.httpStatus, 400);
        QCOMPARE(parse(reply.body).value("error").toObject().value("code").toInt(),
                 int(Mcp::ParseError));

        reply = server->handlePost(R"({"jsonrpc": "1.0", "id": 11, "method": "ping"})");
        QCOMPARE(parse(reply.body).value("error").toObject().value("code").toInt(),
                 int(Mcp::InvalidRequest));

        reply = server->handlePost(R"({"jsonrpc": "2.0", "id": null, "method": "ping"})");
        QCOMPARE(parse(reply.body).value("error").toObject().value("code").toInt(),
                 int(Mcp::InvalidRequest));

        QCOMPARE(server->handlePost("").httpStatus, 400);
        QCOMPARE(server->handlePost("[]").httpStatus, 400);
    }

    void batches()
    {
        QJsonObject received;
        QScopedPointer<Mcp::Server> server(makeServer(&received));
        const auto reply = server->handlePost(
            R"([{"jsonrpc": "2.0", "id": 1, "method": "ping"},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}])");
        QCOMPARE(reply.httpStatus, 200);
        const auto responses = QJsonDocument::fromJson(reply.body).array();
        QCOMPARE(responses.size(), 2);
        QCOMPARE(responses.at(0).toObject().value("id").toInt(), 1);
        QCOMPARE(responses.at(1).toObject().value("id").toInt(), 2);
    }

    void parsesHttpRequests()
    {
        const QByteArray body = R"({"jsonrpc":"2.0","id":1,"method":"ping"})";
        const QByteArray head = "POST /mcp?x=1 HTTP/1.1\r\nHost: 127.0.0.1:9999\r\n"
                                "Content-Type: application/json\r\nContent-Length: "
                                + QByteArray::number(body.size()) + "\r\n\r\n";
        Mcp::HttpRequest request;
        qsizetype consumed = 0;
        QCOMPARE(Mcp::parseHttpRequest(head + body.left(5), request), Mcp::ParseResult::Incomplete);
        QCOMPARE(Mcp::parseHttpRequest(head + body, request, 1024, &consumed),
                 Mcp::ParseResult::Complete);
        QCOMPARE(consumed, head.size() + body.size());
        QCOMPARE(request.method, QByteArray("POST"));
        QCOMPARE(request.path(), QByteArray("/mcp"));
        QCOMPARE(request.header("CONTENT-TYPE"), QByteArray("application/json"));
        QCOMPARE(request.body, body);
        QVERIFY(!request.isWebSocketUpgrade());
        QCOMPARE(Mcp::parseHttpRequest(head + body, request, 10), Mcp::ParseResult::TooLarge);

        const QByteArray chunked = "POST /mcp HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n"
                                   "5\r\nhello\r\n6;x=y\r\n world\r\n0\r\n\r\n";
        QCOMPARE(Mcp::parseHttpRequest(chunked.chopped(2), request), Mcp::ParseResult::Incomplete);
        QCOMPARE(Mcp::parseHttpRequest(chunked, request, 1024, &consumed),
                 Mcp::ParseResult::Complete);
        QCOMPARE(request.body, QByteArray("hello world"));
        QCOMPARE(consumed, chunked.size());

        QCOMPARE(Mcp::parseHttpRequest("GET / HTTP/1.1\r\nUpgrade: websocket\r\n"
                                       "Connection: keep-alive, Upgrade\r\n\r\n",
                                       request),
                 Mcp::ParseResult::Complete);
        QVERIFY(request.isWebSocketUpgrade());
        QVERIFY(Mcp::hasCompleteHeaders("GET / HTTP/1.1\r\n\r\n"));
        QVERIFY(!Mcp::hasCompleteHeaders("GET / HTTP/1.1\r\n"));

        QCOMPARE(Mcp::parseHttpRequest("NONSENSE\r\n\r\n", request), Mcp::ParseResult::Invalid);
        QCOMPARE(Mcp::parseHttpRequest("POST /mcp HTTP/1.1\r\nContent-Length: x\r\n\r\n", request),
                 Mcp::ParseResult::Invalid);
    }

    void onlyLocalOriginsAndHosts_data()
    {
        QTest::addColumn<QByteArray>("value");
        QTest::addColumn<bool>("origin");
        QTest::addColumn<bool>("host");
        QTest::newRow("absent") << QByteArray() << true << true;
        QTest::newRow("localhost") << QByteArray("http://localhost") << true << false;
        QTest::newRow("localhost port") << QByteArray("http://localhost:3000") << true << false;
        QTest::newRow("ipv4 https") << QByteArray("https://127.0.0.1:9999") << true << false;
        QTest::newRow("ipv6") << QByteArray("http://[::1]:9999") << true << false;
        QTest::newRow("evil") << QByteArray("http://evil.example") << false << false;
        QTest::newRow("suffix") << QByteArray("http://localhost.evil.example") << false << false;
        QTest::newRow("prefix") << QByteArray("http://127.0.0.1.evil.example") << false << false;
        QTest::newRow("null") << QByteArray("null") << false << false;
        QTest::newRow("file") << QByteArray("file://") << false << false;
        QTest::newRow("host name") << QByteArray("localhost:9999") << false << true;
        QTest::newRow("host ipv4") << QByteArray("127.0.0.1:9999") << false << true;
        QTest::newRow("host ipv6") << QByteArray("[::1]:9999") << false << true;
        QTest::newRow("host evil") << QByteArray("evil.example:9999") << false << false;
        QTest::newRow("host bad port") << QByteArray("localhost:abc") << false << false;
    }

    void onlyLocalOriginsAndHosts()
    {
        QFETCH(QByteArray, value);
        QFETCH(bool, origin);
        QFETCH(bool, host);
        QCOMPARE(Mcp::isLocalOrigin(value), origin);
        QCOMPARE(Mcp::isLocalHost(value), host);
    }

    void clientConfigurations()
    {
        QCOMPARE(Mcp::clientConfiguration(Mcp::Client::ClaudeCode, 9999, "", "python"),
                 QString("claude mcp add --transport http shotcut-ai http://127.0.0.1:9999/mcp"));

        auto config = parse(
            Mcp::clientConfiguration(Mcp::Client::OpenCode, 9999, "", "python").toUtf8());
        const auto server = config.value("mcp").toObject().value("shotcut-ai").toObject();
        QCOMPARE(server.value("type").toString(), QString("remote"));
        QCOMPARE(server.value("url").toString(), QString("http://127.0.0.1:9999/mcp"));
        QVERIFY(server.value("enabled").toBool());

        const QString bridge = "C:\\Program Files\\Shotcut AI\\share\\shotcut\\mcp\\"
                               "shotcut_mcp_bridge.py";
        for (auto client : {Mcp::Client::ClaudeDesktop, Mcp::Client::Antigravity}) {
            config = parse(Mcp::clientConfiguration(client, 9999, bridge, "python").toUtf8());
            const auto stdio = config.value("mcpServers").toObject().value("shotcut-ai").toObject();
            QCOMPARE(stdio.value("command").toString(), QString("python"));
            QCOMPARE(stdio.value("args").toArray().first().toString(), bridge);
            QVERIFY(!stdio.contains("env"));
        }
        // Another port reaches the bridge through SHOTCUT_AI_URL.
        config = parse(
            Mcp::clientConfiguration(Mcp::Client::ClaudeDesktop, 8765, bridge, "python3").toUtf8());
        const auto stdio = config.value("mcpServers").toObject().value("shotcut-ai").toObject();
        QCOMPARE(stdio.value("env").toObject().value("SHOTCUT_AI_URL").toString(),
                 QString("http://127.0.0.1:8765/mcp"));
    }

    void formatsResponses()
    {
        const auto response
            = Mcp::httpResponse(200, "application/json", "{}", {{"Mcp-Session-Id", "abc"}});
        QVERIFY(response.startsWith("HTTP/1.1 200 OK\r\n"));
        QVERIFY(response.contains("Content-Type: application/json\r\n"));
        QVERIFY(response.contains("Content-Length: 2\r\n"));
        QVERIFY(response.contains("Connection: close\r\n"));
        QVERIFY(response.contains("Mcp-Session-Id: abc\r\n"));
        QVERIFY(response.endsWith("\r\n\r\n{}"));
        QVERIFY(Mcp::httpResponse(202).startsWith("HTTP/1.1 202 Accepted\r\n"));
        QCOMPARE(Mcp::reasonPhrase(403), QByteArray("Forbidden"));
    }
};

QTEST_APPLESS_MAIN(TestMcpProtocol)

#include "test_mcp_protocol.moc"
