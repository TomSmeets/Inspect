#define _GNU_SOURCE
#include <arpa/inet.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static unsigned int DEBUG_DATA[1024] = {
    0x452307a1,         // magic 1
    0x4cae5cf0,         // magic 2
    sizeof(DEBUG_DATA), // max size
    0,                  // used size
};

void *inspect_command_thread(void *arg) {
    int port = (int)(intptr_t)arg;

    // Create TCP socket
    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        exit(EXIT_FAILURE);
    }

    // Allow reusing the port immediately after program exit
    int opt = 1;
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        exit(EXIT_FAILURE);
    }

    // Setup address
    struct sockaddr_in address = {};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY; // Listen on all interfaces
    address.sin_port = htons(port);

    // Bind socket
    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
        exit(EXIT_FAILURE);
    }

    // Listen for connections
    if (listen(server_fd, 1) < 0) {
        exit(EXIT_FAILURE);
    }

    printf("Server listening on port %d...\n", port);

    for (;;) {
        // Accept one client
        socklen_t addrlen = sizeof(address);
        int client_fd = accept(server_fd, (struct sockaddr *)&address, &addrlen);
        if (client_fd < 0) {
            exit(EXIT_FAILURE);
        }

        printf("Client connected.\n");

        for (;;) {
            unsigned char command;
            int n = recv(client_fd, &command, sizeof(command), 0);
            if (n != sizeof(command)) break;

            // Info command
            if (command == 0) {
                void *response = (void *)DEBUG_DATA;
                send(client_fd, &response, sizeof(response), 0);
            }

            // Read data
            if (command == 1) {
                uint64_t args[2];
                recv(client_fd, &args, sizeof(args), 0);
                printf("read %p %lu\n", (void *)args[0], args[1]);
                send(client_fd, (void *)args[0], args[1], 0);
            }

            // Write data
            if (command == 2) {
                uint64_t args[2];
                recv(client_fd, &args, sizeof(args), 0);
                printf("write %p %lu\n", (void *)args[0], args[1]);
                recv(client_fd, (void *)args[0], args[1], 0);
            }
        }
    }
    return 0;
}

static pthread_t command_thread_handle;

void inspect_start(int port) {
    pthread_create(&command_thread_handle, 0, inspect_command_thread, (void *) (intptr_t) port);
}
