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

#ifndef CLIENTSETUP_H
#define CLIENTSETUP_H

#include <QByteArray>
#include <QJsonObject>
#include <QString>
#include <QStringList>

/*!
  \namespace ClientSetup
  \brief Connects AI clients to Shotcut AI without copying and pasting: it adds the MCP
  servers to the configuration file of Claude Desktop.

  It depends only on Qt Core, so it is unit tested without the application
  (tests/test_mcp_protocol.cpp).
*/
namespace ClientSetup {

/// Where Claude Desktop keeps claude_desktop_config.json, in order of preference:
/// - the copy in the folder of a Microsoft Store package of Claude
///   (<localAppData>/Packages/Claude_*/LocalCache/Roaming/Claude), which the app reads
///   instead of the real one when it exists;
/// - the usual file in \a configDir (AppData/Roaming on Windows, Application Support on
///   macOS, ~/.config on Linux).
/// Pass an empty \a localAppData outside Windows.
QStringList claudeDesktopConfigCandidates(const QString &configDir, const QString &localAppData);

/// The file to change among \a candidates: the first that exists; else, the first whose
/// folder exists (Claude Desktop is installed but has no configuration yet); else, the last
/// one (the usual file), or an empty string when there are no candidates.
QString chooseConfigFile(const QStringList &candidates);

enum class MergeResult { Changed, Unchanged, Invalid };

/// Adds or replaces \a servers in the "mcpServers" object of the JSON text \a existing
/// (empty text counts as an empty object) and keeps everything else. On Invalid (not a JSON
/// object, or "mcpServers" is not an object) \a error explains it and \a output is empty.
MergeResult mergeMcpServers(const QByteArray &existing,
                            const QJsonObject &servers,
                            QByteArray &output,
                            QString *error = nullptr);

/// Merges \a servers into the file at \a path, creating it and its folder if needed. A file
/// that already exists is first copied to "<path>.bak". Returns false with \a error set
/// when the file is invalid (it is left as it was) or cannot be written.
bool writeMcpServers(const QString &path, const QJsonObject &servers, QString *error = nullptr);

} // namespace ClientSetup

#endif // CLIENTSETUP_H
