#![cfg_attr(target_os = "windows", windows_subsystem = "windows")]
use std::{env, path::PathBuf, process::{Command, ExitCode, Stdio}};

fn parse(args: impl Iterator<Item=String>) -> Result<(PathBuf, PathBuf, Option<String>), String> {
    let mut args = args;
    let (mut engine, mut data, mut module) = (None, None, None);
    while let Some(arg) = args.next() {
        let value = args.next().ok_or("Missing option value")?;
        match arg.as_str() {
            "--engine" => engine = Some(PathBuf::from(value)),
            "--data-dir" => data = Some(PathBuf::from(value)),
            "--python-module" => module = Some(value),
            _ => return Err("Unknown option".into()),
        }
    }
    Ok((engine.ok_or("Missing engine")?, data.ok_or("Missing data directory")?, module))
}

fn main() -> ExitCode {
    let (engine, data, module) = match parse(env::args().skip(1)) { Ok(v) => v, Err(_) => return ExitCode::from(2) };
    if !engine.is_file() { return ExitCode::from(3); }
    let mut command = Command::new(engine);
    if let Some(module) = module { command.args(["-m", &module]); }
    else { command.arg("--daemon"); }
    command.arg("--data-dir").arg(data).stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null());
    // The engine owns the single-instance lock and task journal. An unexpected
    // exit is not replayed: automatic retry could repeat external side effects.
    match command.spawn().and_then(|mut child| child.wait()) {
        Ok(status) if status.success() => ExitCode::SUCCESS,
        Ok(_) => ExitCode::from(4),
        Err(_) => ExitCode::from(5),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn paths_are_arguments_not_shell_commands() {
        let v=vec!["--engine", "C:\\Program Files\\ARISE.exe", "--data-dir", "C:\\User Data\\ARISE"];
        let parsed=parse(v.into_iter().map(str::to_string)).unwrap();
        assert_eq!(parsed.0, PathBuf::from("C:\\Program Files\\ARISE.exe"));
    }
    #[test] fn rejects_unknown_or_incomplete_options() {
        assert!(parse(vec!["--engine".to_owned()].into_iter()).is_err());
        assert!(parse(vec!["--exec".to_owned(), "anything".to_owned()].into_iter()).is_err());
    }
}
