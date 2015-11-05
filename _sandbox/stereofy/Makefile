CC= g++
CXXFLAGS= -c -O2 -Wall -pedantic
LDFLAGS= -lsndfile
EXEC=stereofy

all: anyoption.o main.o 
	$(CC) anyoption.o main.o $(LDFLAGS) -o $(EXEC) -v # -L /usr/local/lib/ lib path needed to compile on OSX10.10

static: anyoption.o main.o 
	$(CC) -static anyoption.o main.o $(LDFLAGS) -o $(EXEC)-static

main.o: main.cpp 	 
	$(CC) $(CXXFLAGS) main.cpp #-I /usr/local/include/ include path needed to compile on OSX10.10

anyoption.o: anyoption.cpp 	 
	$(CC) $(CXXFLAGS) anyoption.cpp
	
clean:	 
	rm -f ./*.o
	rm -f $(EXEC)
	
