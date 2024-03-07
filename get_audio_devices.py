import pyaudio

# pretty print audio devices and their channels
print("{:<3} {:<50} {:<10} {:<10}".format("ID", "Name", "InChannels", "OutChannels"))

p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    device_info = p.get_device_info_by_index(i)
    print("{:<3} {:<50} {:<10} {:<10}".format(i, device_info.get('name'), device_info.get('maxInputChannels'), device_info.get('maxOutputChannels')))
