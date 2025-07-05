#pragma once
#pragma once

#include <condition_variable>
#include <functional>
#include <mutex>
#include <queue>
#include <thread>
#include <vector>

using namespace std;

// Class that represents a simple thread pool
class ThreadPool {
public:
    // Constructor to create a thread pool with a given number of threads
    explicit ThreadPool(size_t num_threads = std::thread::hardware_concurrency());

    // Destructor to stop all threads and clean up resources
    ~ThreadPool();

    // Enqueue task for execution by the thread pool
    void enqueue(std::function<void()> task);

private:
    // Vector to store worker threads
    vector<std::thread> threads_;

    // Queue of tasks to be executed
    queue<std::function<void()>> tasks_;

    // Mutex to synchronize access to shared data
    mutex queue_mutex_;

    // Condition variable to signal changes in the state of the tasks queue
    condition_variable cv_;

    // Flag to indicate whether the thread pool should stop or not
    bool stop_ = false;
};
