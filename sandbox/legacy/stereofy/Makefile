CC= g++
CXXFLAGS= -c -O2 -Wall -pedantic
LDFLAGS= -lsndfile
EXEC=stereofy

all: anyoption.o main.o 
	$(CC) anyoption.o main.o $(LDFLAGS) -o $(EXEC)

static: anyoption.o main.o 
	$(CC) -static anyoption.o main.o $(LDFLAGS) -o $(EXEC)-static

main.o: main.cpp 	 
	$(CC) $(CXXFLAGS) main.cpp

anyoption.o: anyoption.cpp 	 
	$(CC) $(CXXFLAGS) anyoption.cpp
	
clean:	 
	rm ./*.o
	rm $(EXEC)
	
