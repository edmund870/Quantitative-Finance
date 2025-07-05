#include "ThreadPool.h"
#include <iostream>

// Constructor to create a thread pool with the given number of threads
ThreadPool::ThreadPool(size_t num_threads) {
    // Create the worker threads
    for (size_t i = 0; i < num_threads; ++i) {
        threads_.emplace_back([this] {
            while (true) {
                std::function<void()> task;

                // Locking the queue to safely access it
                {
                    std::unique_lock<std::mutex> lock(queue_mutex_);
                    // Wait for a task or a stop signal
                    cv_.wait(lock, [this] { return !tasks_.empty() || stop_; });

                    // If stop flag is true and no tasks are in the queue, exit the thread
                    if (stop_ && tasks_.empty()) {
                        return;
                    }

                    // Get the next task
                    task = std::move(tasks_.front());
                    tasks_.pop();
                }

                // Execute the task
                task();
            }
            });
    }
}

// Destructor to stop all threads and clean up resources
ThreadPool::~ThreadPool() {
    {
        std::unique_lock<std::mutex> lock(queue_mutex_);
        stop_ = true;  // Set the stop flag to true
    }

    // Notify all threads to stop if they are waiting
    cv_.notify_all();

    // Join all threads to ensure they finish execution
    for (auto& thread : threads_) {
        thread.join();
    }
}

// Enqueue a task for execution by the thread pool
void ThreadPool::enqueue(std::function<void()> task) {
    {
        // Lock the queue to add the new task
        std::unique_lock<std::mutex> lock(queue_mutex_);
        tasks_.push(std::move(task));
    }
    // Notify one of the threads that a task is available
    cv_.notify_one();
}
