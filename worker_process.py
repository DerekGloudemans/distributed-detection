# -*- coding: utf-8 -*-
"""
Created on Wed Nov  6 18:48:14 2019
@author: Derek Gloudemans

This file contains the function that creates a worker process
"""
import threading
import multiprocessing as mp
import queue
import random

from worker_thread_fns import ( receive_images,send_messages,receive_messages,
                               load_balance,heartbeat,work_function )


def worker(hosts,ports,audit_rate,worker_num, timeout = 20, VERBOSE = False):
    """
    Given a list of hosts and ports (one pair for each worker) and an id num,
    creates a series of threads and shared variables that carry out the work in
    a decentralized manner
    """
    
    # define shared variables
    p_image_queue = queue.Queue() # for storing received images
    p_new_id_queue = queue.Queue() # for storing received image names
    p_message_queue = queue.Queue() # for storing messages to send
    p_task_queue = queue.Queue() # for storing tasks assigned to worker
    p_lb_results = queue.Queue() # for storing load balancing results
    p_audit_queue = queue.Queue() # for storing audit requests
    
    # since shared variables across threads in multiple processes is a bit of a pain,
    # a queue is used even though the value it stores is a float
    p_average_time = queue.Queue()
    p_average_time.put(1+0.01*worker_num) # initialize with a bit of difference
    
    
    
    # get sender port
    host = hosts[worker_num]
    port = ports[worker_num]
    
    # get receiver ports
    hosts.remove(host)
    ports.remove(port)
    
    # create image receiver thread
    thread_im_rec = threading.Thread(target = receive_images, args = 
                                     (p_image_queue,
                                      p_new_id_queue,
                                      "127.0.0.1",
                                      6200,
                                      timeout,
                                      VERBOSE, 
                                      worker_num))
    
    # create message sender thread
    t_mes_send = threading.Thread(target = send_messages, args = 
                                     (host,
                                     port,
                                     p_message_queue,
                                     timeout,
                                     VERBOSE,
                                     worker_num))
    
    # create message receiver thread
    t_mes_recv = threading.Thread(target = receive_messages, args = 
                                    (hosts,
                                    ports,
                                    p_lb_results,
                                    timeout,
                                    VERBOSE,
                                    worker_num))
    
    # create load balancer thread
    t_load_bal = threading.Thread(target = load_balance, args = 
                                    (p_new_id_queue,
                                    p_task_queue,
                                    p_lb_results,
                                    p_message_queue,
                                    p_average_time,
                                    timeout,
                                    1.1,
                                    True, #verbose
                                    worker_num))
    
    t_heartbeat = threading.Thread(target = heartbeat, args =
                                   (p_average_time,
                                    p_message_queue,
                                    p_task_queue,
                                    0.5,
                                    timeout,
                                    VERBOSE,
                                    worker_num))
    
    t_work = threading.Thread(target = work_function, args = 
                              (p_image_queue,
                               p_task_queue,
                               p_audit_queue,
                               p_message_queue,
                               audit_rate, # shared across all processes
                               p_average_time,
                               timeout,
                               True,
                               worker_num, 
                               len(ports)+1)) # total number of workers
                                    
    
    # start all threads
    thread_im_rec.start()
    t_mes_recv.start()
    t_mes_send.start()
    t_load_bal.start() 
    t_heartbeat.start()
    
    # wait for all threads to terminate
    thread_im_rec.join()
    t_mes_recv.join()
    t_mes_send.join()
    t_load_bal.join()  
    t_heartbeat.join()
    

if __name__ == "__main__":
    # tester code for the worker processes
    
    hosts = []
    ports = []
    num_workers = 3
    timeout = 20
    VERBOSE = False
    audit_rate = mp.Value('f',0.1,lock = True)
    
    for i in range(num_workers):
        hosts.append("127.0.0.1")
        ports.append(5200+i)
    
    processes = []
    for i in range(num_workers):
        p = mp.Process(target = worker, args = (hosts,ports,audit_rate,i,timeout,VERBOSE,))
        p.start()
        processes.append(p)
    print("All processes started")
    
    for p in processes:
        p.join()
    print("All processes terminated")    
    