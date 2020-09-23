import functools
import gzip
import struct
import zlib

TAG_END = 0
TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_FLOAT = 5
TAG_DOUBLE = 6
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10
TAG_INT_ARRAY = 11
TAG_LONG_ARRAY = 12

# NBT tag data model and interface
class NBT:
    # Contructor, does NOT decode/decompress
    def __init__(self, ID=0, payload=None, name=None, compression=None):
    
            # Tag ID
            self.ID = ID
            
            # Tag payload
            if payload is not None and self.ID != 0:
                self.payload = payload
                    
            # Tag name
            if name is not None:
                self.name = name
                
            # Compression method
            if compression is not None:
                self.compression = compression

    # Test if two tags are the same
    def __eq__(self, other):
        if type(other) != NBT:
            return False
        elif self.ID != other.ID:
            return False
        else:
            # For arrays / compounds / lists
            if (
                self.ID == TAG_BYTE_ARRAY 
                or self.ID == TAG_LIST
                or self.ID == TAG_COMPOUND
                or self.ID == TAG_INT_ARRAY
                or self.ID == TAG_LONG_ARRAY
            ):
                # Make one iteratable out of both
                zipped = zip(self.payload, other.payload)
                # Recursively compare all values
                for selfElement, otherElement in zipped:
                    if selfElement != otherElement:
                        print(f'Element mismatch with {selfElement} and {otherElement}')
                        return False
                        break
                else:
                    return True
                    
            elif self.ID == 0:
                return True
            else:
                return self.payload == other.payload
    
    # Length of array tags
    def __len__(self):
        return len(self.payload)

    # Subscript accessor override
    def __getitem__(self, key):
        return self.payload[key]
    
    # Subscript assignment override
    def __setitem__(self, key, value):

        # ID of item
        itemID = self[key].ID

        # Check types ==
        if type(value) != type(self[key].payload):
            raise TypeError (f'Cannot assign {str(type(value))} to {self[key].typeStr}')
           
        # Check value is within bounds
        if itemID <= 6:
            if itemID == TAG_BYTE:
                minimum = 0
                maximum = 255
                
            elif itemID == TAG_SHORT or itemID == TAG_INT or itemID == TAG_LONG:
                minimum = -2**( 8*(itemID-1) )
                maximum = 2**( 8*(itemID-1) ) -1
                
            elif itemID == TAG_FLOAT or itemID == TAG_DOUBLE:
                minimum = -2**( 8*(itemID-3) )
                maximum = 2**( 8*(itemID-3) ) -1
                
            if value<minimum or value>maximum:
                raise ValueError( f'Value for {self[key].typeStr} must be between {minimum} and {maximum}')
                
        # Assign Value
        self[key].payload = value
    
    # Returns SNBT
    def __repr__(self):
    
        snbt = ''
        if self.ID == TAG_END:
            pass
        elif (
            self.ID == TAG_BYTE 
            or self.ID == TAG_SHORT
            or self.ID == TAG_INT 
            or self.ID == TAG_LONG 
            or self.ID == TAG_DOUBLE 
            or self.ID == TAG_FLOAT
        ):
         
            snbt += str(self.payload)
            
            # Choose letter to append to value
            if self.ID == TAG_BYTE:
                snbt += 'b'
            elif self.ID == TAG_SHORT:
                snbt += 's'
            elif self.ID == TAG_LONG:
                snbt += 'l'
            elif self.ID == TAG_FLOAT:
                snbt += 'f'
            elif self.ID == TAG_DOUBLE:
                snbt += 'd'
            
        elif self.ID == TAG_STRING:
            
            # Opening quote
            snbt += '\''
            
            # Write characters, escape quotes
            for character in self.payload:
                if character == '\'':
                    # Both backslash and quote need escaping, hence the \\\
                    snbt += '\\\''
                else:
                    snbt += character
                
            # Closing quote
            snbt += '\''
                
        elif (
            self.ID==TAG_BYTE_ARRAY 
            or self.ID==TAG_LIST 
            or self.ID==TAG_INT_ARRAY 
            or self.ID==TAG_LONG_ARRAY
        ):
            
            # Opening square bracket
            snbt += '['
            
            if self.ID == TAG_BYTE_ARRAY:
                snbt += 'B;'
            elif self.ID == TAG_INT_ARRAY:
                snbt += 'I;'
            elif self.ID == TAG_LONG_ARRAY:
                snbt += 'L;'
            
            # Used to know if comma needed
            i = len(self.payload)
            
            for element in self.payload:
                snbt += repr(element)
                
                # Add comma if not last item
                i -= 1
                if i > 0:
                    snbt += ','

            # Closing square bracket
            snbt += ']'
            
        elif self.ID == TAG_COMPOUND:
            
            # Opening Curly Bracket
            snbt += '{'
            
            # Used to know if comma needed
            i = len(self.payload)
            
            # Add all elements
            for element in self.payload:
                snbt += f'{element}:{self[element]}'
                
                # Add comma if not last item
                i -= 1
                if i > 0:
                    snbt += ','
                
            # Closing Curly Bracket
            snbt += '}'
            
        return snbt

    # Alias of __repr__
    def __str__(self):
        return repr(self)
        
    # Decodes (compressed) bytes -> NBT
    @classmethod
    def decode(cls, nbt = b'\x00', compression = None):

        # Decode individual payload
        def decode_payload(ID):
            
            # TagIDs are only defined up to 12
            if ID > 12:
                raise RuntimeError('Invalid tagID : ' + str(ID) )
                
            elif ID == TAG_END:
                return
                
            elif ID == TAG_COMPOUND:
            
                payload = {}
                for itemID in iter(functools.partial(decode_payload, ID=TAG_BYTE), TAG_END):
                    itemName = decode_payload(TAG_STRING)
                    itemPayload = decode_payload(itemID)
                    payload[itemName] = cls(ID=itemID, payload=itemPayload)
                return payload
                
            else:
                
                if (
                    ID == TAG_BYTE_ARRAY 
                    or ID == TAG_LIST 
                    or ID == TAG_INT_ARRAY 
                    or ID == TAG_LONG_ARRAY
                ):
                
                    # Find recursive element ID
                    if ID == TAG_BYTE_ARRAY:
                        itemID = TAG_BYTE
                        
                    elif ID == TAG_LIST:
                        itemID = decode_payload(TAG_BYTE)
                        
                    elif ID == TAG_INT_ARRAY:
                        itemID = TAG_INT
                        
                    elif ID == TAG_LONG_ARRAY:
                        itemID = TAG_LONG
                
                    # Make Payload
                    size = decode_payload(TAG_INT)
                    return [cls(ID=itemID, payload=decode_payload(itemID)) for i in range(size)]
                        
                else:
                    # Calculate length
                    if (
                        ID == TAG_BYTE 
                        or ID == TAG_SHORT 
                        or ID == TAG_INT 
                        or ID == TAG_LONG
                    ):
                        payloadLength = 2 ** (ID-1)
                        
                    elif ID == TAG_FLOAT or ID == TAG_DOUBLE:
                        payloadLength = 2 ** (ID-3)
                        
                    elif ID == TAG_STRING:
                        payloadLength = decode_payload(TAG_SHORT)
                    
                    # Read Payload
                    payload = bytearray()
                    try:
                        for i in range(payloadLength):
                            nextByte = nbt.__next__()
                            if type(nextByte) == int:
                                payload.append(nextByte)
                            elif type(nextByte) == bytes:
                                payload += nextByte
                            # Sometimes the file returns ints and sometimes bytes
                            # If I ever find out why maybe I can simplify this
                            # Probably to a list comprehension
                    except StopIteration:
                        pass

                    # Format Payload
                    if ID == TAG_BYTE:
                        return int.from_bytes(payload, byteorder='big')
                        
                    elif (
                        ID == TAG_SHORT 
                        or ID == TAG_INT 
                        or ID == TAG_LONG
                    ):
                        return int.from_bytes(payload, byteorder='big', signed=True)
                        
                    elif ID == TAG_FLOAT:
                        return struct.unpack('>f', payload)[0]
                    
                    elif ID == TAG_DOUBLE:
                        return struct.unpack('>d', payload)[0]
                        
                    elif ID == TAG_STRING:
                        try:
                            # This is str.decode, not NBT.decode
                            return payload.decode()
                        except UnicodeDecodeError:
                            raise RuntimeError('Cannot decode '+ str(payload) +' to unicode')
          
        # Try all methods if compression is unknown
        if compression is None:
            for tryCompression in [1,2,3]:
                try:
                    return cls.decode(nbt, tryCompression)
                except:
                    continue
            # Runs if all compression methods failed
            raise RuntimeError('Unknown compression method.')

        # Decompress and decode
        else:
        
            # Decompresss input
            if compression == 1:
                nbt = gzip.decompress(nbt)
            elif compression == 2:
                nbt = zlib.decompress(nbt)
            elif compression == 3:
                # 3 means no compression
                pass
            else:
                raise ValueError(f'Unknown compression method {compression}')
        
            # Make input iteratable,
            nbt = nbt.__iter__()
            
            # Get data
            tagID = decode_payload(TAG_BYTE)
            tagName = decode_payload(TAG_STRING)
            tagPayload = decode_payload(tagID)
            
            # Format as NBT
            return NBT(
                ID=tagID, 
                name=tagName, 
                payload=tagPayload,
                compression = compression
            )

    # Encodes NBT -> (compressed) bytes
    def encode(self, newCompression = None):
    
        # Encode individual payload
        def encode_payload(ID : int, tagPayload):
            # TagIDs are only defined up to 12
            if ID > 12:
                raise RuntimeError( 'Invalid tagID : ' + str(ID) )
                
            # Create empty payload
            payload = bytearray()
            
            if ID == TAG_COMPOUND:
                for element in tagPayload:
                    # Recursively encode
                    payload += encode_payload(TAG_BYTE, tagPayload[element].ID)
                    payload += encode_payload(TAG_STRING, element)
                    payload += encode_payload(tagPayload[element].ID, tagPayload[element].payload)
                payload += (b'\x00')
                
            else:
                # For recursives
                if (
                    ID == TAG_BYTE_ARRAY 
                    or ID == TAG_LIST 
                    or ID == TAG_INT_ARRAY
                    or ID == TAG_LONG_ARRAY
                ):
                
                    if ID == TAG_LIST:
                        # Find elementID
                        try:
                            elementID = tagPayload[0].ID
                        except IndexError:
                            elementID = TAG_END
                            
                        # Store elementID in payload
                        payload += encode_payload(TAG_BYTE, elementID)
                        
                    # Store length in payload 
                    payload += encode_payload(TAG_INT, len(tagPayload))
                    
                    # Make Payload
                    for element in tagPayload:
                        payload += encode_payload(element.ID, element.payload)
                    
                # For non-recursives
                else:
                    if ID == TAG_BYTE:
                        payload += tagPayload.to_bytes(length=1, byteorder='big')
                        
                    elif (
                        ID == TAG_SHORT
                        or ID == TAG_INT
                        or ID == TAG_LONG
                    ):
                            payload += tagPayload.to_bytes(length=(2**(ID-1)), byteorder='big', signed=True)
                        
                    elif ID == TAG_FLOAT:
                        payload += struct.pack('>f', tagPayload)
                        
                    elif ID == TAG_DOUBLE:
                        payload += struct.pack('>d', tagPayload)
                        
                    elif ID == TAG_STRING:
                        # For strings
                        tagPayload = tagPayload.encode()
                        payload += encode_payload(TAG_SHORT, len(tagPayload))
                        payload += tagPayload
                    
            return payload
        
        payload = bytearray()
        
        # Make self payload
        payload += encode_payload(TAG_BYTE, self.ID)
        try:
            payload += encode_payload(TAG_STRING, self.name)
        except AttributeError:
            pass
        payload += encode_payload(self.ID, self.payload)
            
        # Find out compression method
        try:
            compression = newCompression if newCompression is not None else self.compression
        except AttributeError:
            # If compression is undefined, do not compress
            compression = 3
            
        # Compress payload
        # Recursions use 3, only outermost is compressed
        if compression == 1:
            payload = gzip.compress(payload)
        elif compression == 2:
            payload = zlib.compress(payload)
        elif compression == 3:
            # 3 means no compression
            pass
        else:
            raise ValueError(f'Unknown compression method {compression}')

        return payload

    # Get subtags, if applicable
    def keys(self):
        return self.payload.keys()
        
    # Returns tag type str of ID
    @property
    def typeStr(self):
        def IDstr(ID):
            if ID == TAG_END:
                return 'TAG_End'
            elif ID == TAG_BYTE:
                return 'TAG_Byte'
            elif ID == TAG_SHORT:
                return 'TAG_Short'
            elif ID == TAG_INT:
                return 'TAG_Int'
            elif ID == TAG_LONG:
                return 'TAG_Long'
            elif ID == TAG_FLOAT:
                return 'TAG_Float'
            elif ID == TAG_DOUBLE:
                return 'TAG_Double'
            elif ID == TAG_BYTE_ARRAY:
                return 'TAG_Byte_Array'
            elif ID == TAG_STRING:
                return 'TAG_String'
            elif ID == TAG_LIST:
                return 'TAG_List'
            elif ID == TAG_COMPOUND:
                return 'TAG_Compound'
            elif ID == TAG_INT_ARRAY:
                return 'TAG_Int_Array'
            elif ID == TAG_LONG_ARRAY:
                return 'TAG_Long_Array'
                
        if self.ID == 9:
            try:
                return f'{IDstr(self.ID)}({IDstr(elementID)})'
            except IndexError:
                return f'{IDstr(self.ID)}({IDstr(TAG_END)})'
        else:
            return IDstr(self.ID)
        