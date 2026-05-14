---
type: lecture
course: Operating Systems
source_file: Lecture_4_-_Threads.pptx
date: 2026-05-13
tags: [lecture, Operating Systems, threads]
---

# Chapter 4: Threads

## Key concepts

- **Thread** (lightweight process): Unit of execution within a process; smallest unit of dispatching by the OS
- **Process**: Unit of resource allocation and unit of protection; owns address space, registers, program counter, stack
- **Multithreading**: OS ability to support multiple concurrent paths of execution within a single process
- **Single-threaded process**: Contains one thread; one unit of execution
- **Multithreaded process**: Contains multiple threads sharing the same address space and resources
- **Thread operations**: Spawn (create new thread), Block (wait for event), Unblock (move to ready queue), Finish (deallocate resources)
- **Thread states**: Running, Ready, Blocked (suspend states don't apply to threads—they're process-level concepts)
- **User-Level Threads (ULTs)**: All thread management done by application; kernel unaware of threads
- **Kernel-Level Threads (KLTs)**: Thread management done entirely by kernel; requires kernel API
- **Combined approach**: Thread creation in user space, scheduling/synchronization mostly by application, mapped to kernel threads
- **Concurrency vs Parallelism**: Concurrency is illusion on single processor (time-sharing); parallelism is true simultaneous execution on multiprocessor systems

## Worked examples

**MS Word Multithreaded Application:**
- Thread A: Manage keyboard input
- Thread B: Manage print function (allows user to continue editing while printing)
- Thread C: Manage save function

**Thread execution sequence example:** 6A, 2B, 6A, 3A (represents unit of execution/thread of instructions)

**Multiprocess vs Multithreaded Applications:**
- Google Chrome: Multiprocess (each tab is separate single-threaded process)
- Excel/Office: Multithreaded native application (small number of highly threaded processes)
- Java applications: Embrace threading fundamentally via JVM and language design

## Study cards

- Q: What is the primary difference between a process and a thread? | A: A process is the unit of resource allocation and protection; a thread is the unit of execution and dispatching. Threads within a process share the same address space and resources.

- Q: Name four key benefits of using threads instead of separate processes. | A: (1) Thread creation is ~10x faster than process creation; (2) Thread termination is faster; (3) Context switching between threads is faster; (4) Threads in same process communicate without kernel intervention (shared memory/files).

- Q: What are the four basic thread operations and their purposes? | A: Spawn—create new thread with instruction pointer and args; Block—thread waits for event, saves context; Unblock—event occurred, move thread to ready queue; Finish—deallocate thread's registers and stack.

- Q: What is the main disadvantage of User-Level Threads (ULTs)? | A: Blocking system calls block the entire process (all threads). Also, ULTs cannot utilize multiprocessing—only one thread can execute at a time since kernel assigns one process to one processor.

- Q: What is the main disadvantage of Kernel-Level Threads (KLTs)? | A: Mode switch to kernel required for thread context switching within the same process, adding overhead. KLTs are also slower to create and manage than ULTs.

- Q: What are two key advantages of Kernel-Level Threads? | A: (1) Multiple threads from same process can run on different processors simultaneously; (2) Blocking of one thread doesn't block others—kernel can schedule another thread from same process.

- Q: Describe the combined ULT/KLT approach used in Solaris. | A: Thread creation happens in user space; application does bulk of scheduling and synchronization. Multiple ULTs are mapped onto fewer (or equal) KLTs, allowing parallel execution on multiprocessors while avoiding some overhead of pure KLTs.

- Q: In what four ways are threads useful in single-user systems? | A: (1) Foreground/background work (UI thread + processing thread); (2) Asynchronous processing (backup thread runs independently); (3) Speed of execution (one thread reads I/O while another computes); (4) Modular program structure (cleaner design).

- Q: Why is thread scheduling done on a thread basis rather than process basis? | A: In thread-supporting OS, scheduling and dispatching occurs at thread granularity; most state information for execution lives in thread-level data structures. However, some actions (e.g., address space swap, process termination) affect all threads and must be managed at process level.

- Q: What three advantages does ULT have over KLT? | A: (1) No kernel mode switch required—all thread management in user space saves overhead; (2) Scheduling can be application-specific/optimized; (3) ULTs work on any OS without kernel modification.

## Open questions

- How does the threads library in ULTs decide which ready thread to schedule next, and can this be preempted by the OS?
- What synchronization primitives (locks, semaphores, condition variables) are available for inter-thread communication?
- How do the kernel and user-space schedulers coordinate in a combined ULT/KLT system to avoid starvation?
- What happens to a thread's stack and register state during a context switch?
- How are signals and asynchronous events handled differently in ULT vs KLT systems?
