#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <termios.h>
#include <fcntl.h>
#include <time.h>
#include <string.h>

#define WIDTH 40
#define HEIGHT 5
#define MAX_JUMP 2

int player_y = HEIGHT - 1;
int jump_ticks = 0;
int jump_count = 0;
int jumping = 0;
int obstacles[WIDTH] = {0};
int score = 0;
int highscore = 0;
int lives = 3;
int speed_us = 140000;
int obstacle_cooldown = 0;

void set_conio_terminal_mode() {
    struct termios new_termios;
    tcgetattr(0, &new_termios);
    new_termios.c_lflag &= ~(ICANON | ECHO);
    tcsetattr(0, TCSANOW, &new_termios);
}

int kbhit() {
    struct timeval tv = { 0L, 0L };
    fd_set fds;
    FD_ZERO(&fds);
    FD_SET(0, &fds);
    return select(1, &fds, NULL, NULL, &tv);
}

int getch() {
    int r;
    unsigned char c;
    if ((r = read(0, &c, sizeof(c))) < 0) return 0;
    else return c;
}

void clear_screen() {
    printf("\033[2J\033[H");
}

void play_sound(const char* file) {
    char cmd[128];
    snprintf(cmd, sizeof(cmd), "afplay %s &>/dev/null &", file);
    system(cmd);
}

void load_highscore() {
    FILE *file = fopen("highscore.txt", "r");
    if (file) {
        fscanf(file, "%d", &highscore);
        fclose(file);
    }
}

void save_highscore() {
    FILE *file = fopen("highscore.txt", "w");
    if (file) {
        fprintf(file, "%d", highscore);
        fclose(file);
    }
}

void draw() {
    char screen[HEIGHT][WIDTH];

    for (int y = 0; y < HEIGHT; y++)
        for (int x = 0; x < WIDTH; x++)
            screen[y][x] = ' ';

    for (int i = 0; i < WIDTH; i++) {
        if (obstacles[i])
            screen[HEIGHT - 1][i] = '#';
    }

    screen[player_y][1] = 'O';

    for (int y = 0; y < HEIGHT; y++) {
        for (int x = 0; x < WIDTH; x++) {
            if (screen[y][x] == 'O') printf("\033[1;32mO\033[0m");
            else if (screen[y][x] == '#') printf("\033[1;31m#\033[0m");
            else putchar(screen[y][x]);
        }
        putchar('\n');
    }

    printf("Score: %d | Highscore: %d | Lives: %d\n", score, highscore, lives);
}

void update() {
    for (int i = 0; i < WIDTH - 1; i++) {
        obstacles[i] = obstacles[i + 1];
    }

    if (obstacle_cooldown <= 0 && (rand() % 10 > 7)) {
        obstacles[WIDTH - 1] = 1;
        obstacle_cooldown = 5;
    } else {
        obstacles[WIDTH - 1] = 0;
        obstacle_cooldown--;
    }

    if (obstacles[0]) score++;

    if (score % 10 == 0 && speed_us > 60000)
        speed_us -= 2000;

    // Jump logic
    if (jumping) {
        if (jump_ticks < 4) {
            player_y = HEIGHT - 2;
            jump_ticks++;
        } else {
            jumping = 0;
        }
    } else {
        player_y = HEIGHT - 1;
        jump_ticks = 0;
    }
}

int check_collision() {
    return obstacles[1] && player_y == HEIGHT - 1;
}

void handle_input() {
    if (kbhit()) {
        int ch = getch();
        if (ch == ' ') {
            if (jump_count < MAX_JUMP) {
                jumping = 1;
                jump_count++;
            }
        }
    }

    // Reset jump if on ground
    if (player_y == HEIGHT - 1) {
        jump_count = 0;
    }
}

void game_loop() {
    player_y = HEIGHT - 1;
    jump_ticks = 0;
    jump_count = 0;
    jumping = 0;
    memset(obstacles, 0, sizeof(obstacles));
    score = 0;
    speed_us = 140000;
    obstacle_cooldown = 0;
    lives = 3;

    while (1) {
        clear_screen();
        draw();
        handle_input();
        update();

        if (check_collision()) {
            lives--;
            play_sound("/System/Library/Sounds/Funk.aiff");
            if (lives == 0) {
                clear_screen();
                printf("💥 Game Over!\n");
                if (score > highscore) {
                    printf("🏆 Neuer Highscore: %d!\n", score);
                    highscore = score;
                    save_highscore();
                } else {
                    printf("Endstand: %d | Highscore: %d\n", score, highscore);
                }
                printf("\nDrücke eine Taste für das Menü...");
                getch();
                break;
            } else {
                // Rücksetzpause
                printf("❗ Du hast ein Leben verloren. Weiter in 2 Sekunden...\n");
                sleep(2);
                player_y = HEIGHT - 1;
                jump_count = 0;
                jumping = 0;
                jump_ticks = 0;
            }
        }

        usleep(speed_us);
    }
}

void show_highscore() {
    clear_screen();
    printf("🏆 Aktueller Highscore: %d\n", highscore);
    printf("\nDrücke eine Taste, um zurückzukehren...");
    getch();
}

void menu() {
    char choice;
    while (1) {
        clear_screen();
        printf("=== TERMINAL JUMP DELUXE ===\n");
        printf("[1] Spiel starten\n");
        printf("[2] Highscore ansehen\n");
        printf("[3] Beenden\n");
        printf("> ");
        choice = getch();

        if (choice == '1') {
            game_loop();
        } else if (choice == '2') {
            show_highscore();
        } else if (choice == '3') {
            clear_screen();
            printf("👋 Bis bald!\n");
            exit(0);
        }
    }
}

int main() {
    srand(time(NULL));
    set_conio_terminal_mode();
    load_highscore();
    menu();
    return 0;
}
