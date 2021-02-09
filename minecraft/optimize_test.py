import datetime
import minecraft
import os
import time

totalSaved = 0
totalOldSize = 0
totalTime = 0

regionDir = r'C:\Users\ambro\AppData\Roaming\.minecraft\saves\world\region'
oldRegionDir = r'C:\Users\ambro\AppData\Roaming\.minecraft\saves\world\region - Copy'
totalFiles = len(os.listdir(regionDir))

for i in os.listdir(regionDir):
    newFile = os.path.join(regionDir, i)
    oldFile = os.path.join(oldRegionDir, i)
    newMca = minecraft.McaFile.open(newFile)
    oldMca = minecraft.McaFile.open(oldFile)
    print(f'{datetime.datetime.now()} Optimizing {newFile}...')
    startTime = time.time()
    newMca.optimize()
    endTime = time.time()
    totalTime += endTime - startTime

    print(f'{datetime.datetime.now()} Checking {newFile} for corruption...')
    for x in range(32):
        for z in range(32):
            try:
                oldChunk = oldMca[x,z]
            except FileNotFoundError:
                chunkExisted = False
            else:
                chunkExisted = True
            
            try:
                newChunk = newMca[x,z]
            except FileNotFoundError:
                chunkCopied = False
            else:
                chunkCopied = True
            
            if chunkCopied and not chunkExisted:
                raise RuntimeError(f'Somehow invented chunk {x}, {z}')
            elif not chunkCopied and chunkExisted:
                raise RuntimeError(f'Failed to copy chunk {x}, {z}')
            if chunkCopied and chunkExisted and newChunk != oldChunk:
                raise RuntimeError(f'Corrupted chunk {x} {z}')

    oldSize = os.stat(oldFile).st_size
    newSize = os.stat(newFile).st_size
    savedSize = oldSize - newSize
    savedPercent = round((savedSize / oldSize) * 100, 1)
    totalOldSize += oldSize
    totalSaved += savedSize
    print(f'{datetime.datetime.now()} Optimized {oldSize} to {newSize} (saved {savedSize} bytes, or {savedPercent}%)')

totalPercent = round((totalSaved / totalOldSize) * 100, 1)
averageSaved = totalSaved/totalFiles
print(f'{datetime.datetime.now()} Saved {totalSaved} bytes in total, or {totalPercent}% (average {averageSaved} bytes) in {totalTime} seconds')