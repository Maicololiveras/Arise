//! A daemon and its descendants are owned by the host, not by executable names.
use std::{ffi::c_void, os::windows::io::AsRawHandle, process::Child};
type Handle = *mut c_void;
#[repr(C)]
#[derive(Default)]
struct BasicLimits {
    process_time: i64, job_time: i64, flags: u32, min_working_set: usize,
    max_working_set: usize, active_processes: u32, affinity: usize,
    priority: u32, scheduling: u32,
}
#[repr(C)]
#[derive(Default)]
struct ExtendedLimits {
    basic: BasicLimits, io: [u64;6], process_memory: usize, job_memory: usize,
    peak_process_memory: usize, peak_job_memory: usize,
}
#[link(name="kernel32")]
unsafe extern "system" {
    fn CreateJobObjectW(attributes: Handle, name: *const u16) -> Handle;
    fn SetInformationJobObject(job: Handle, class: i32, information: Handle, length: u32) -> i32;
    fn AssignProcessToJobObject(job: Handle, process: Handle) -> i32;
    fn CloseHandle(handle: Handle) -> i32;
}
pub struct Job(Handle);
impl Job {
    pub fn own(child: &Child) -> std::io::Result<Self> {
        unsafe {
            let handle=CreateJobObjectW(std::ptr::null_mut(),std::ptr::null());
            if handle.is_null() {return Err(std::io::Error::last_os_error());}
            let job=Self(handle);
            let mut limits=ExtendedLimits::default(); limits.basic.flags=0x2000; // KILL_ON_JOB_CLOSE
            if SetInformationJobObject(handle,9,(&mut limits as *mut ExtendedLimits).cast(),std::mem::size_of::<ExtendedLimits>() as u32)==0 || AssignProcessToJobObject(handle,child.as_raw_handle())==0 {
                return Err(std::io::Error::last_os_error());
            }
            Ok(job)
        }
    }
}
impl Drop for Job {fn drop(&mut self) {unsafe {CloseHandle(self.0);}}}
#[cfg(test)] mod tests {
    use super::*;
    #[test] fn uses_windows_x64_native_layout() {
        assert_eq!(std::mem::size_of::<BasicLimits>(),64);
        assert_eq!(std::mem::size_of::<ExtendedLimits>(),144);
    }
}
