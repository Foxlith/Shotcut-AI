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

#include "mcpprotocol.h"

#include <cmath>
#include <QJsonDocument>
#include <QUrl>

namespace Mcp {

ToolResult ToolResult::success(const QJsonObject &data, const QString &text)
{
    ToolResult result;
    result.data = data;
    result.text = text;
    return result;
}

ToolResult ToolResult::failure(const QString &message)
{
    ToolResult result;
    result.text = message;
    result.isError = true;
    return result;
}

QJsonObject ToolResult::toJson() const
{
    QJsonArray content;
    QString message = text;
    if (message.isEmpty() && !data.isEmpty())
        message = QString::fromUtf8(QJsonDocument(data).toJson(QJsonDocument::Compact));
    if (!message.isEmpty())
        content.append(QJsonObject{{"type", "text"}, {"text", message}});
    for (const auto &block : extraContent)
        content.append(block);
    QJsonObject result{{"content", content}, {"isError", isError}};
    if (!isError && !data.isEmpty())
        result["structuredContent"] = data;
    return result;
}

QJsonObject Tool::toJson() const
{
    QJsonObject object{{"name", name}, {"description", description}, {"inputSchema", inputSchema}};
    if (!title.isEmpty())
        object["title"] = title;
    if (!annotations.isEmpty())
        object["annotations"] = annotations;
    return object;
}

Server::Server(const QString &name,
               const QString &title,
               const QString &version,
               const QString &instructions)
    : m_name(name)
    , m_title(title)
    , m_version(version)
    , m_instructions(instructions)
{}

void Server::addTool(const Tool &tool)
{
    if (m_toolIndex.contains(tool.name)) {
        m_tools[m_toolIndex.value(tool.name)] = tool;
    } else {
        m_toolIndex.insert(tool.name, m_tools.size());
        m_tools.append(tool);
    }
}

const Tool *Server::tool(const QString &name) const
{
    const auto it = m_toolIndex.constFind(name);
    return it == m_toolIndex.constEnd() ? nullptr : &m_tools.at(it.value());
}

QStringList Server::toolNames() const
{
    QStringList names;
    for (const auto &tool : m_tools)
        names << tool.name;
    return names;
}

ToolResult Server::callTool(const QString &name, const QJsonObject &arguments) const
{
    const Tool *t = tool(name);
    if (!t)
        return ToolResult::failure(QStringLiteral("Unknown tool: %1. Available tools: %2")
                                       .arg(name, toolNames().join(", ")));
    const auto problem = validateArguments(t->inputSchema, arguments);
    if (!problem.isEmpty())
        return ToolResult::failure(
            QStringLiteral("Invalid arguments for %1: %2").arg(name, problem));
    if (!t->handler)
        return ToolResult::failure(QStringLiteral("The tool %1 is not available.").arg(name));
    return t->handler(arguments);
}

QStringList Server::protocolVersions()
{
    return {QStringLiteral("2025-11-25"),
            QStringLiteral("2025-06-18"),
            QStringLiteral("2025-03-26"),
            QStringLiteral("2024-11-05")};
}

QString Server::negotiateVersion(const QString &requested)
{
    const auto versions = protocolVersions();
    return versions.contains(requested) ? requested : versions.first();
}

QJsonObject Server::errorResponse(const QJsonValue &id, int code, const QString &message)
{
    return QJsonObject{{"jsonrpc", "2.0"},
                       {"id", id.isUndefined() ? QJsonValue(QJsonValue::Null) : id},
                       {"error", QJsonObject{{"code", code}, {"message", message}}}};
}

QJsonObject Server::initializeResult(const QJsonObject &params) const
{
    QJsonObject serverInfo{{"name", m_name}, {"version", m_version}};
    if (!m_title.isEmpty())
        serverInfo["title"] = m_title;
    QJsonObject result{{"protocolVersion",
                        negotiateVersion(params.value("protocolVersion").toString())},
                       {"capabilities", QJsonObject{{"tools", QJsonObject{{"listChanged", false}}}}},
                       {"serverInfo", serverInfo}};
    if (!m_instructions.isEmpty())
        result["instructions"] = m_instructions;
    return result;
}

bool Server::handleMessage(const QJsonObject &message, QJsonObject &response) const
{
    const QJsonValue id = message.value("id");
    const bool hasId = message.contains("id");
    if (!message.contains("method")) {
        // A response to a server request (this server sends none) needs no answer.
        if (message.contains("result") || message.contains("error"))
            return false;
        response = errorResponse(id, InvalidRequest, "Invalid request: missing method");
        return true;
    }
    if (message.value("jsonrpc").toString() != QLatin1String("2.0")) {
        if (!hasId)
            return false;
        response = errorResponse(id, InvalidRequest, "Invalid request: jsonrpc must be \"2.0\"");
        return true;
    }
    const QJsonValue methodValue = message.value("method");
    if (!methodValue.isString()) {
        response = errorResponse(id, InvalidRequest, "Invalid request: method must be a string");
        return true;
    }
    const QString method = methodValue.toString();
    // Notifications (no id), such as notifications/initialized, need no response.
    if (!hasId)
        return false;
    if (!id.isString() && !id.isDouble()) {
        response = errorResponse(QJsonValue::Null,
                                 InvalidRequest,
                                 "Invalid request: id must be a string or a number");
        return true;
    }
    const QJsonValue paramsValue = message.value("params");
    if (!paramsValue.isUndefined() && !paramsValue.isObject() && !paramsValue.isNull()) {
        response = errorResponse(id, InvalidParams, "Invalid params: params must be an object");
        return true;
    }
    const QJsonObject params = paramsValue.toObject();

    QJsonObject result;
    if (method == QLatin1String("initialize")) {
        result = initializeResult(params);
    } else if (method == QLatin1String("ping") || method == QLatin1String("logging/setLevel")) {
        // Empty result.
    } else if (method == QLatin1String("tools/list")) {
        QJsonArray tools;
        for (const auto &tool : m_tools)
            tools.append(tool.toJson());
        result["tools"] = tools;
    } else if (method == QLatin1String("tools/call")) {
        const QJsonValue name = params.value("name");
        if (!name.isString()) {
            response = errorResponse(id, InvalidParams, "Invalid params: missing tool name");
            return true;
        }
        const QJsonValue arguments = params.value("arguments");
        if (!arguments.isUndefined() && !arguments.isObject() && !arguments.isNull()) {
            response = errorResponse(id,
                                     InvalidParams,
                                     "Invalid params: arguments must be an object");
            return true;
        }
        if (!tool(name.toString())) {
            response = errorResponse(id,
                                     InvalidParams,
                                     QStringLiteral("Unknown tool: %1").arg(name.toString()));
            return true;
        }
        result = callTool(name.toString(), arguments.toObject()).toJson();
    } else if (method == QLatin1String("resources/list")) {
        // Not offered (see the capabilities), but some clients ask anyway.
        result["resources"] = QJsonArray();
    } else if (method == QLatin1String("resources/templates/list")) {
        result["resourceTemplates"] = QJsonArray();
    } else if (method == QLatin1String("prompts/list")) {
        result["prompts"] = QJsonArray();
    } else {
        response = errorResponse(id,
                                 MethodNotFound,
                                 QStringLiteral("Method not found: %1").arg(method));
        return true;
    }
    response = QJsonObject{{"jsonrpc", "2.0"}, {"id", id}, {"result", result}};
    return true;
}

Server::Reply Server::handlePost(const QByteArray &body) const
{
    auto errorReply = [](int code, const QString &message) {
        return Reply{400,
                     QJsonDocument(errorResponse(QJsonValue::Null, code, message))
                         .toJson(QJsonDocument::Compact)};
    };
    if (body.trimmed().isEmpty())
        return errorReply(InvalidRequest, "Invalid request: empty body");
    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(body, &error);
    if (error.error != QJsonParseError::NoError)
        return errorReply(ParseError, QStringLiteral("Parse error: %1").arg(error.errorString()));

    if (document.isArray()) {
        const auto messages = document.array();
        if (messages.isEmpty())
            return errorReply(InvalidRequest, "Invalid request: empty batch");
        QJsonArray responses;
        for (const auto &value : messages) {
            QJsonObject response;
            if (!value.isObject())
                responses.append(errorResponse(QJsonValue::Null,
                                               InvalidRequest,
                                               "Invalid request: not an object"));
            else if (handleMessage(value.toObject(), response))
                responses.append(response);
        }
        if (responses.isEmpty())
            return Reply{202, QByteArray()};
        return Reply{200, QJsonDocument(responses).toJson(QJsonDocument::Compact)};
    }
    if (!document.isObject())
        return errorReply(InvalidRequest, "Invalid request: not a JSON-RPC message");
    QJsonObject response;
    if (!handleMessage(document.object(), response))
        return Reply{202, QByteArray()};
    return Reply{200, QJsonDocument(response).toJson(QJsonDocument::Compact)};
}

static QString typeName(const QJsonValue &value)
{
    switch (value.type()) {
    case QJsonValue::Null:
        return QStringLiteral("null");
    case QJsonValue::Bool:
        return QStringLiteral("boolean");
    case QJsonValue::Double:
        return QStringLiteral("number");
    case QJsonValue::String:
        return QStringLiteral("string");
    case QJsonValue::Array:
        return QStringLiteral("array");
    case QJsonValue::Object:
        return QStringLiteral("object");
    default:
        return QStringLiteral("undefined");
    }
}

static bool hasType(const QJsonValue &value, const QString &type)
{
    if (type == QLatin1String("integer")) {
        if (!value.isDouble())
            return false;
        const double number = value.toDouble();
        return std::isfinite(number) && std::floor(number) == number;
    }
    if (type == QLatin1String("number"))
        return value.isDouble();
    return typeName(value) == type;
}

static QString checkObject(const QJsonObject &schema,
                           const QJsonObject &object,
                           const QString &path);

static QString checkValue(const QJsonObject &schema, const QJsonValue &value, const QString &path)
{
    const QJsonValue typeValue = schema.value("type");
    QStringList types;
    if (typeValue.isString())
        types << typeValue.toString();
    else if (typeValue.isArray())
        for (const auto &type : typeValue.toArray())
            types << type.toString();
    if (!types.isEmpty()) {
        bool matches = false;
        for (const auto &type : types)
            matches = matches || hasType(value, type);
        if (!matches)
            return QStringLiteral("%1 must be %2, not %3")
                .arg(path, types.join(QStringLiteral(" or ")), typeName(value));
    }
    if (schema.contains("enum")) {
        const auto choices = schema.value("enum").toArray();
        if (!choices.contains(value)) {
            QStringList names;
            for (const auto &choice : choices)
                names << QString::fromUtf8(QJsonDocument(QJsonArray{choice})
                                               .toJson(QJsonDocument::Compact)
                                               .mid(1)
                                               .chopped(1));
            return QStringLiteral("%1 must be one of %2").arg(path, names.join(", "));
        }
    }
    if (value.isDouble()) {
        const double number = value.toDouble();
        if (schema.contains("minimum") && number < schema.value("minimum").toDouble())
            return QStringLiteral("%1 must be at least %2")
                .arg(path)
                .arg(schema.value("minimum").toDouble());
        if (schema.contains("maximum") && number > schema.value("maximum").toDouble())
            return QStringLiteral("%1 must be at most %2")
                .arg(path)
                .arg(schema.value("maximum").toDouble());
    }
    if (value.isArray()) {
        const auto items = value.toArray();
        if (schema.contains("minItems") && items.size() < schema.value("minItems").toInt())
            return QStringLiteral("%1 needs at least %2 item(s)")
                .arg(path)
                .arg(schema.value("minItems").toInt());
        if (schema.value("items").isObject()) {
            const auto itemSchema = schema.value("items").toObject();
            for (int i = 0; i < items.size(); ++i) {
                const auto problem = checkValue(itemSchema,
                                                items.at(i),
                                                QStringLiteral("%1[%2]").arg(path).arg(i));
                if (!problem.isEmpty())
                    return problem;
            }
        }
    }
    if (value.isObject() && (schema.contains("properties") || schema.contains("required")))
        return checkObject(schema, value.toObject(), path);
    return QString();
}

static QString checkObject(const QJsonObject &schema, const QJsonObject &object, const QString &path)
{
    const auto prefix = path.isEmpty() ? QString() : path + QLatin1Char('.');
    for (const auto &required : schema.value("required").toArray()) {
        const auto name = required.toString();
        if (!object.contains(name) || object.value(name).isNull())
            return QStringLiteral("missing required argument \"%1%2\"").arg(prefix, name);
    }
    const auto properties = schema.value("properties").toObject();
    const bool closed = schema.value("additionalProperties").isBool()
                        && !schema.value("additionalProperties").toBool();
    for (auto it = object.constBegin(); it != object.constEnd(); ++it) {
        if (!properties.contains(it.key())) {
            if (closed)
                return QStringLiteral("unknown argument \"%1%2\"; valid arguments: %3")
                    .arg(prefix, it.key(), properties.keys().join(", "));
            continue;
        }
        // An explicit null is the same as leaving an optional argument out.
        if (it.value().isNull())
            continue;
        const auto problem = checkValue(properties.value(it.key()).toObject(),
                                        it.value(),
                                        QStringLiteral("\"%1%2\"").arg(prefix, it.key()));
        if (!problem.isEmpty())
            return problem;
    }
    return QString();
}

QString Server::validateArguments(const QJsonObject &schema, const QJsonObject &arguments)
{
    return checkObject(schema, arguments, QString());
}

QByteArray HttpRequest::header(const QByteArray &name) const
{
    return headers.value(name.toLower());
}

QByteArray HttpRequest::path() const
{
    const auto query = target.indexOf('?');
    return query < 0 ? target : target.left(query);
}

bool HttpRequest::isWebSocketUpgrade() const
{
    return header("upgrade").trimmed().toLower() == "websocket"
           && header("connection").toLower().contains("upgrade");
}

bool hasCompleteHeaders(const QByteArray &data)
{
    return data.contains("\r\n\r\n");
}

ParseResult parseHttpRequest(const QByteArray &data,
                             HttpRequest &request,
                             qsizetype maxBodySize,
                             qsizetype *consumed)
{
    static const qsizetype kMaxHeaderSize = 64 * 1024;
    const auto headerEnd = data.indexOf("\r\n\r\n");
    if (headerEnd < 0)
        return data.size() > kMaxHeaderSize ? ParseResult::TooLarge : ParseResult::Incomplete;
    if (headerEnd > kMaxHeaderSize)
        return ParseResult::TooLarge;

    request = HttpRequest();
    const auto lines = data.left(headerEnd).split('\n');
    const auto requestLine = lines.first().trimmed().split(' ');
    if (requestLine.size() != 3 || !requestLine.at(2).startsWith("HTTP/1.")
        || requestLine.at(0).isEmpty() || !requestLine.at(1).startsWith('/'))
        return ParseResult::Invalid;
    request.method = requestLine.at(0);
    request.target = requestLine.at(1);
    for (qsizetype i = 1; i < lines.size(); ++i) {
        const auto line = lines.at(i).trimmed();
        if (line.isEmpty())
            continue;
        const auto colon = line.indexOf(':');
        if (colon <= 0)
            return ParseResult::Invalid;
        const auto name = line.left(colon).trimmed().toLower();
        const auto value = line.mid(colon + 1).trimmed();
        if (request.headers.contains(name))
            request.headers[name] += ", " + value;
        else
            request.headers.insert(name, value);
    }

    const qsizetype bodyStart = headerEnd + 4;
    if (request.header("transfer-encoding").toLower().contains("chunked")) {
        qsizetype position = bodyStart;
        QByteArray body;
        while (true) {
            const auto lineEnd = data.indexOf("\r\n", position);
            if (lineEnd < 0)
                return ParseResult::Incomplete;
            auto sizeText = data.mid(position, lineEnd - position);
            const auto extension = sizeText.indexOf(';');
            if (extension >= 0)
                sizeText = sizeText.left(extension);
            bool ok = false;
            const qsizetype size = sizeText.trimmed().toLongLong(&ok, 16);
            if (!ok || size < 0)
                return ParseResult::Invalid;
            position = lineEnd + 2;
            if (size == 0) {
                // Skip any trailer fields up to the empty line.
                const auto end = data.indexOf("\r\n", position);
                if (end < 0)
                    return ParseResult::Incomplete;
                if (end != position) {
                    const auto trailersEnd = data.indexOf("\r\n\r\n", position);
                    if (trailersEnd < 0)
                        return ParseResult::Incomplete;
                    position = trailersEnd + 4;
                } else {
                    position = end + 2;
                }
                break;
            }
            if (body.size() + size > maxBodySize)
                return ParseResult::TooLarge;
            if (data.size() < position + size + 2)
                return ParseResult::Incomplete;
            body += data.mid(position, size);
            position += size + 2;
        }
        request.body = body;
        if (consumed)
            *consumed = position;
        return ParseResult::Complete;
    }

    const auto lengthText = request.header("content-length");
    qsizetype length = 0;
    if (!lengthText.isEmpty()) {
        bool ok = false;
        length = lengthText.toLongLong(&ok);
        if (!ok || length < 0)
            return ParseResult::Invalid;
        if (length > maxBodySize)
            return ParseResult::TooLarge;
    }
    if (data.size() - bodyStart < length)
        return ParseResult::Incomplete;
    request.body = data.mid(bodyStart, length);
    if (consumed)
        *consumed = bodyStart + length;
    return ParseResult::Complete;
}

static bool isLoopbackHostName(const QString &host)
{
    const auto name = host.toLower();
    return name == QLatin1String("localhost") || name == QLatin1String("127.0.0.1")
           || name == QLatin1String("::1") || name == QLatin1String("[::1]");
}

bool isLocalOrigin(const QByteArray &origin)
{
    const auto text = origin.trimmed();
    if (text.isEmpty())
        return true;
    const QUrl url(QString::fromLatin1(text), QUrl::StrictMode);
    if (!url.isValid() || (!url.path().isEmpty() && url.path() != QLatin1String("/"))
        || !url.userInfo().isEmpty() || url.hasQuery())
        return false;
    if (url.scheme() != QLatin1String("http") && url.scheme() != QLatin1String("https"))
        return false;
    return isLoopbackHostName(url.host());
}

bool isLocalHost(const QByteArray &host)
{
    auto text = QString::fromLatin1(host.trimmed());
    if (text.isEmpty())
        return true;
    if (text.startsWith(QLatin1Char('['))) {
        const auto close = text.indexOf(QLatin1Char(']'));
        if (close < 0)
            return false;
        const auto rest = text.mid(close + 1);
        if (!rest.isEmpty() && !rest.startsWith(QLatin1Char(':')))
            return false;
        text = text.left(close + 1);
    } else {
        const auto colon = text.indexOf(QLatin1Char(':'));
        if (colon >= 0) {
            bool ok = false;
            text.mid(colon + 1).toUShort(&ok);
            if (!ok)
                return false;
            text = text.left(colon);
        }
    }
    return isLoopbackHostName(text);
}

QByteArray reasonPhrase(int status)
{
    switch (status) {
    case 100:
        return "Continue";
    case 200:
        return "OK";
    case 202:
        return "Accepted";
    case 400:
        return "Bad Request";
    case 403:
        return "Forbidden";
    case 404:
        return "Not Found";
    case 405:
        return "Method Not Allowed";
    case 413:
        return "Payload Too Large";
    case 415:
        return "Unsupported Media Type";
    case 431:
        return "Request Header Fields Too Large";
    case 503:
        return "Service Unavailable";
    default:
        return status < 500 ? "Bad Request" : "Internal Server Error";
    }
}

QString clientConfiguration(Client client,
                            quint16 port,
                            const QString &bridgePath,
                            const QString &python)
{
    const auto url = QStringLiteral("http://127.0.0.1:%1/mcp").arg(port);
    QJsonObject config;
    switch (client) {
    case Client::ClaudeCode:
        return QStringLiteral("claude mcp add --transport http shotcut-ai %1").arg(url);
    case Client::OpenCode:
        // opencode.json
        config = QJsonObject{{"$schema", "https://opencode.ai/config.json"},
                             {"mcp",
                              QJsonObject{{"shotcut-ai",
                                           QJsonObject{{"type", "remote"},
                                                       {"url", url},
                                                       {"enabled", true}}}}}};
        break;
    case Client::ClaudeDesktop:
    case Client::Antigravity: {
        // claude_desktop_config.json and mcp_config.json start a local process: the bridge.
        QJsonObject stdio{{"command", python}, {"args", QJsonArray{bridgePath}}};
        if (port != 9999)
            stdio["env"] = QJsonObject{{"SHOTCUT_AI_URL", url}};
        config = QJsonObject{{"mcpServers", QJsonObject{{"shotcut-ai", stdio}}}};
        break;
    }
    }
    return QString::fromUtf8(QJsonDocument(config).toJson(QJsonDocument::Indented));
}

QByteArray httpResponse(int status,
                        const QByteArray &contentType,
                        const QByteArray &body,
                        const QList<QPair<QByteArray, QByteArray>> &headers)
{
    QByteArray response = "HTTP/1.1 " + QByteArray::number(status) + ' ' + reasonPhrase(status)
                          + "\r\n";
    if (!contentType.isEmpty())
        response += "Content-Type: " + contentType + "\r\n";
    response += "Content-Length: " + QByteArray::number(body.size()) + "\r\n";
    response += "Cache-Control: no-store\r\n";
    response += "Connection: close\r\n";
    for (const auto &header : headers)
        response += header.first + ": " + header.second + "\r\n";
    response += "\r\n";
    response += body;
    return response;
}

} // namespace Mcp
