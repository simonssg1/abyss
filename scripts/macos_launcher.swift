// Lanceur natif d'Abyss (compilé par build_macos_launcher.sh).
// Il lance `uv run --project <dépôt> abyss` comme processus enfant : macOS attribue ainsi les
// autorisations (micro, Accessibilité, Surveillance de l'entrée) à « Abyss » et non à uv/Python.
// Un nouveau double-clic relance la commande, qui ramène la fenêtre existante au premier plan.
import Cocoa

let repo = "__REPO__"
let uv = "__UV__"

func logHandle() -> FileHandle? {
    let dir = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".abyss/logs")
    try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
    let file = dir.appendingPathComponent("launcher.log")
    if !FileManager.default.fileExists(atPath: file.path) {
        FileManager.default.createFile(atPath: file.path, contents: nil)
    }
    let handle = try? FileHandle(forWritingTo: file)
    handle?.seekToEndOfFile()
    return handle
}

final class Launcher: NSObject, NSApplicationDelegate {
    let log = logHandle()

    @discardableResult
    func launch() -> Process {
        let fmt = DateFormatter()
        fmt.dateFormat = "yyyy-MM-dd HH:mm:ss"
        let stamp = fmt.string(from: Date())
        log?.write("=== \(stamp) lancement d'Abyss\n".data(using: .utf8)!)
        let p = Process()
        p.executableURL = URL(fileURLWithPath: uv)
        p.arguments = ["run", "--project", repo, "abyss"]
        p.currentDirectoryURL = URL(fileURLWithPath: repo)
        if let log = log {
            p.standardOutput = log
            p.standardError = log
        }
        do { try p.run() } catch {
            log?.write("Échec du lancement : \(error)\n".data(using: .utf8)!)
        }
        return p
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        let main = launch()
        main.terminationHandler = { _ in DispatchQueue.main.async { NSApp.terminate(nil) } }
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        launch()  // l'instance unique d'Abyss ramène sa fenêtre et ce second processus se termine
        return false
    }
}

let app = NSApplication.shared
let delegate = Launcher()
app.delegate = delegate
app.setActivationPolicy(.accessory)  // pas d'icône pour le lanceur : seule la fenêtre d'Abyss apparaît
app.run()
