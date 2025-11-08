class App {
  public:
  int value1 = 4;

  private:
  int value2 = 4;

  public:
};

static App app = {};

unsigned int DEBUG_DATA[1024] = {
    0x452307a1, 0x4cae5cf0, // Magic Value
    sizeof(DEBUG_DATA),     // Buffer size
};

int main() {
  return app.value1;
}
