//! Dependency-free Socratopia launcher.
//!
//! Rust handles CLI parsing, workspace isolation and read-only inspection.
//! Existing Python modules remain the sole owners of course-state mutations.

use std::env;
use std::ffi::{OsStr, OsString};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode};

const HELP: &str = "\
Socratopia · Pi/Cherry local CLI

Usage:
  socratopia [--root PATH] status --course NAME  # read-only file snapshot
  socratopia [--root PATH] init plan|apply|wizard ...
  socratopia [--root PATH] group configure|status|start|record|continue|stop ...
  socratopia [--root PATH] timer start|status|heartbeat|pause|resume|finish|interrupt ...
  socratopia [--root PATH] prep chapter|new|check|status ...
  socratopia [--root PATH] article plan|import|fetch|study ...
  socratopia [--root PATH] doctor            # Python strict doctor + full tests
  socratopia [--root PATH] preflight [--course NAME]
  socratopia [--root PATH] context --course NAME ...
  socratopia [--root PATH] help

Run from the project directory or supply --root. No shell is used.
This launcher does not replace Python course/runtime validators.
";

fn script_for(command: &str) -> Option<&'static str> {
    match command {
        "init" => Some("initialize.py"),
        "group" => Some("learning_group.py"),
        "timer" => Some("lesson_timer.py"),
        "prep" => Some("prep.py"),
        "article" => Some("web_article.py"),
        "context" => Some("context_pack.py"),
        "course" => Some("course_runtime.py"),
        "preflight" => Some("cherry_preflight.py"),
        "doctor" => Some("check.py"),
        "search" => Some("local_search.py"),
        "review" => Some("review.py"),
        "handoff" => Some("handoff.py"),
        "tasks" => Some("task_queue.py"),
        "memory" => Some("memory.py"),
        "package" => Some("package_release.py"),
        _ => None,
    }
}

fn has_project_files(root: &Path) -> bool {
    root.join("AGENTS.md").is_file()
        && root.join("manifest.json").is_file()
        && root.join("scripts").is_dir()
}

fn find_root(from: &Path, explicit: Option<&Path>) -> Result<PathBuf, String> {
    if let Some(root) = explicit {
        let path = root.canonicalize().map_err(|e| format!("项目根目录不可访问: {e}"))?;
        if has_project_files(&path) {
            return Ok(path);
        }
        return Err(format!("不是 Socratopia 仓库目录: {}", path.display()));
    }
    for ancestor in from.ancestors() {
        if has_project_files(ancestor) {
            return ancestor
                .canonicalize()
                .map_err(|e| format!("解析工作目录失败: {e}"));
        }
    }
    Err("未发现 Socratopia 仓库；请在仓库内运行或指定 --root PATH".into())
}

fn valid_course(raw: &str) -> Result<(), String> {
    let course = raw.trim();
    if course.is_empty()
        || course.starts_with('.')
        || course.contains('/')
        || course.contains('\\')
        || course.contains('\0')
        || course == "."
        || course == ".."
    {
        return Err("课程名必须是单层安全目录名".into());
    }
    Ok(())
}

fn not_symlink(path: &Path) -> Result<(), String> {
    if let Ok(meta) = fs::symlink_metadata(path) {
        if meta.file_type().is_symlink() {
            return Err(format!("拒绝符号链接课程路径: {}", path.display()));
        }
    }
    Ok(())
}

fn snapshot(root: &Path, course: &str) -> Result<Vec<(&'static str, bool)>, String> {
    valid_course(course)?;
    let data_top = root.join("DATA");
    let book_top = root.join("TEXTBOOK");
    not_symlink(&data_top)?;
    not_symlink(&book_top)?;
    let data = data_top.join(course);
    let book = book_top.join(course);
    not_symlink(&data)?;
    not_symlink(&book)?;
    Ok(vec![
        ("course_data_exists", data.is_dir()),
        ("textbook_directory_exists", book.is_dir()),
        ("book_exists", book.join("book.md").is_file()),
        ("progress_exists", data.join("PROGRESS.md").is_file()),
        ("runtime_exists", data.join("runtime/course_state.json").is_file()),
        ("timer_exists", data.join("runtime/lesson_timer.json").is_file()),
        ("learning_group_exists", data.join("runtime/learning_group.json").is_file()),
    ])
}

fn status_command(root: &Path, args: &[OsString]) -> Result<(), String> {
    if args.len() != 2 || args[0] != OsStr::new("--course") {
        return Err("用法: socratopia status --course NAME".into());
    }
    let course = args[1]
        .to_str()
        .ok_or("课程名称必须是有效 UTF-8 文本")?;
    let facts = snapshot(root, course)?;
    println!("course: {}", course.trim());
    for (key, present) in facts {
        println!("{key}: {}", if present { "present" } else { "missing" });
    }
    println!("ready_to_teach: unverified");
    println!("cherry_tool_access: unverified");
    println!("note: file presence is not runtime/PREP validation; run preflight and the Python gates");
    Ok(())
}

fn python_interpreter() -> OsString {
    env::var_os("SOCRATOPIA_PYTHON").unwrap_or_else(|| {
        if cfg!(windows) {
            OsString::from("python")
        } else {
            OsString::from("python3")
        }
    })
}

fn forward(root: &Path, command: &str, args: &[OsString]) -> Result<i32, String> {
    let filename = script_for(command).ok_or_else(|| format!("未知子命令: {command}"))?;
    let scripts = root.join("scripts");
    not_symlink(&scripts)?;
    let script = scripts.join(filename);
    not_symlink(&script)?;
    if !script.is_file() {
        return Err(format!("所需脚本不存在: {}", script.display()));
    }
    let mut process = Command::new(python_interpreter());
    process.arg(&script);
    if command == "doctor" {
        // One canonical strict verification path.
        process.arg("--strict");
    }
    process.args(args).current_dir(root);
    let result = process.status().map_err(|e| format!("启动 Python CLI 失败: {e}"))?;
    Ok(result.code().unwrap_or(1))
}

fn run(args: &[OsString], cwd: &Path) -> Result<i32, String> {
    if args.is_empty()
        || args.first().is_some_and(|a| {
            a == OsStr::new("help") || a == OsStr::new("-h") || a == OsStr::new("--help")
        })
    {
        print!("{HELP}");
        return Ok(0);
    }
    if args.len() == 1 && args[0] == OsStr::new("--version") {
        println!("socratopia {}", env!("CARGO_PKG_VERSION"));
        return Ok(0);
    }
    let mut offset = 0;
    let mut explicit: Option<PathBuf> = None;
    if args.first().is_some_and(|a| a == OsStr::new("--root")) {
        let value = args.get(1).ok_or("--root 需要工作目录路径")?;
        explicit = Some(PathBuf::from(value));
        offset = 2;
    }
    let command = args
        .get(offset)
        .and_then(|a| a.to_str())
        .ok_or("需要合法的子命令；运行 socratopia help 查看说明")?;
    let root = find_root(cwd, explicit.as_deref())?;
    let rest = &args[offset + 1..];
    if command == "status" {
        status_command(&root, rest)?;
        return Ok(0);
    }
    forward(&root, command, rest)
}

fn main() -> ExitCode {
    let args: Vec<OsString> = env::args_os().skip(1).collect();
    let cwd = match env::current_dir() {
        Ok(value) => value,
        Err(error) => {
            eprintln!("ERROR: 无法读取当前目录: {error}");
            return ExitCode::FAILURE;
        }
    };
    match run(&args, &cwd) {
        Ok(0) => ExitCode::SUCCESS,
        Ok(code) => ExitCode::from(u8::try_from(code).unwrap_or(1)),
        Err(error) => {
            eprintln!("ERROR: {error}");
            ExitCode::FAILURE
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    static NEXT: AtomicUsize = AtomicUsize::new(0);

    fn temp_project() -> PathBuf {
        let id = NEXT.fetch_add(1, Ordering::Relaxed);
        let root = env::temp_dir().join(format!("socratopia-rust-test-{}-{id}", std::process::id()));
        fs::create_dir_all(root.join("scripts")).expect("create scripts");
        fs::write(root.join("AGENTS.md"), "test").expect("write AGENTS");
        fs::write(root.join("manifest.json"), "{}").expect("write manifest");
        root
    }

    #[test]
    fn supported_commands_map_only_to_known_scripts() {
        assert_eq!(script_for("group"), Some("learning_group.py"));
        assert_eq!(script_for("init"), Some("initialize.py"));
        assert_eq!(script_for("doctor"), Some("check.py"));
        assert_eq!(script_for("bad;rm -rf x"), None);
    }

    #[test]
    fn discovers_nested_project_without_hardcoded_absolute_path() {
        let root = temp_project();
        fs::create_dir_all(root.join("nested/deeper")).expect("nested");
        let found = find_root(&root.join("nested/deeper"), None).expect("repo found");
        assert_eq!(found, root.canonicalize().expect("canonical root"));
        fs::remove_dir_all(root).expect("cleanup");
    }

    #[test]
    fn missing_or_invalid_workspace_is_rejected() {
        let root = temp_project();
        let empty = root.join("empty");
        fs::create_dir_all(&empty).expect("empty");
        assert!(find_root(&empty, Some(&empty)).is_err());
        assert!(find_root(&root, Some(&root)).is_ok());
        fs::remove_dir_all(root).expect("cleanup");
    }

    #[test]
    fn course_path_validation_matches_python_single_segment_rule() {
        for bad in ["", ".", "..", "../escape", "a/b", "a\\b", ".hidden", "a\0b"] {
            assert!(valid_course(bad).is_err(), "{bad:?}");
        }
        for good in ["遗传学", "Maize-2026", "foo.bar"] {
            assert!(valid_course(good).is_ok(), "{good:?}");
        }
    }

    #[test]
    fn status_is_read_only_and_does_not_invent_readiness() {
        let root = temp_project();
        let before: Vec<_> = fs::read_dir(&root).expect("list").count().to_string().chars().collect();
        let values = snapshot(&root, "遗传学").expect("snapshot");
        assert!(values.iter().all(|(_, present)| !present));
        let after: Vec<_> = fs::read_dir(&root).expect("list").count().to_string().chars().collect();
        assert_eq!(before, after);
        assert!(!root.join("DATA").exists());
        fs::remove_dir_all(root).expect("cleanup");
    }

    #[test]
    fn explicit_status_command_never_accepts_unknown_flags() {
        let root = temp_project();
        let args = vec![OsString::from("--course"), OsString::from("a")];
        assert!(status_command(&root, &args).is_ok());
        assert!(status_command(&root, &[OsString::from("--course")]).is_err());
        fs::remove_dir_all(root).expect("cleanup");
    }
}
