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

/*
 * "Shotcut AI.exe": the program at the top of the portable folder. It has the icon of
 * Shotcut AI (a .bat file cannot have one) and starts bin\shotcut.exe with the same
 * arguments, so double-clicking it or dropping files on it works like the real program.
 *
 * Built by scripts/bundle-windows-msys2.sh:
 *   windres shotcut-ai-launcher.rc -O coff -o launcher.res
 *   gcc -municode -mwindows -O2 shotcut-ai-launcher.c launcher.res -o "Shotcut AI.exe"
 */

#include <stdlib.h>
#include <wchar.h>
#include <windows.h>

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR arguments, int show)
{
    (void) instance;
    (void) previous;
    (void) show;

    wchar_t folder[32768];
    const DWORD length = GetModuleFileNameW(NULL, folder, 32768);
    if (length == 0 || length >= 32768)
        return 1;
    wchar_t *slash = wcsrchr(folder, L'\\');
    if (slash)
        *slash = L'\0';

    const size_t size = wcslen(folder) + wcslen(arguments) + 64;
    wchar_t *program = malloc(size * sizeof(wchar_t));
    wchar_t *commandLine = malloc(size * sizeof(wchar_t));
    if (!program || !commandLine)
        return 1;
    swprintf(program, size, L"%ls\\bin\\shotcut.exe", folder);
    swprintf(commandLine, size, L"\"%ls\" %ls", program, arguments);

    STARTUPINFOW startup = {0};
    startup.cb = sizeof(startup);
    PROCESS_INFORMATION process = {0};
    if (!CreateProcessW(program, commandLine, NULL, NULL, FALSE, 0, NULL, NULL, &startup,
                        &process)) {
        wchar_t message[1024];
        swprintf(message,
                 1024,
                 L"Shotcut AI could not start:\n%ls\n\nExtract the whole zip file and keep the "
                 L"bin folder next to this program.",
                 program);
        MessageBoxW(NULL, message, L"Shotcut AI", MB_ICONERROR | MB_OK);
        return 1;
    }
    // Let the new window come to the front.
    AllowSetForegroundWindow(process.dwProcessId);
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    free(program);
    free(commandLine);
    return 0;
}
