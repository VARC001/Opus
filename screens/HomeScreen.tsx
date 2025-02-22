import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  FlatList,
  Dimensions,
  Animated,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialIcons } from '@expo/vector-icons';
import Slider from '@react-native-community/slider';
import * as MediaLibrary from 'expo-media-library';
import { Audio } from 'expo-av';

const { width } = Dimensions.get('window');

const themes = {
  purple: {
    primary: '#6C63FF',
    secondary: '#5A52E5',
    gradient: ['#2D3436', '#000000'],
    text: '#FFFFFF',
  },
  blue: {
    primary: '#0A84FF',
    secondary: '#0066CC',
    gradient: ['#0A84FF', '#000000'],
    text: '#FFFFFF',
  },
  green: {
    primary: '#30D158',
    secondary: '#248A3D',
    gradient: ['#30D158', '#000000'],
    text: '#FFFFFF',
  },
};

export default function MusicPlayer() {
  const [songs, setSongs] = useState([]);
  const [currentSong, setCurrentSong] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackInstance, setPlaybackInstance] = useState(null);
  const [currentTheme, setCurrentTheme] = useState('purple');
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(0);
  const spinValue = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    loadAudioFiles();
    setupAudio();
  }, []);

  useEffect(() => {
    spinValue.stopAnimation();
    spinValue.setValue(0);
    if (isPlaying) {
      Animated.loop(
        Animated.timing(spinValue, {
          toValue: 1,
          duration: 10000,
          useNativeDriver: true,
        })
      ).start();
    }
  }, [isPlaying, spinValue]);

  const spin = spinValue.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  const loadAudioFiles = async () => {
    try {
      const { status } = await MediaLibrary.requestPermissionsAsync();
      if (status === 'granted') {
        const media = await MediaLibrary.getAssetsAsync({
          mediaType: 'audio',
        });
        setSongs(media.assets);
        if (media.assets.length > 0) {
          const firstSong = media.assets[0];
          setCurrentSong(firstSong);
        }
      }
    } catch (error) {
      console.log('Error loading audio files:', error);
    }
  };

  const setupAudio = async () => {
    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        playsInSilentModeIOS: true,
        staysActiveInBackground: true,
        shouldDuckAndroid: true,
      });
    } catch (error) {
      console.log('Error setting up audio:', error);
    }
  };

  const onPlaybackStatusUpdate = (status) => {
    if (status.isLoaded) {
      setPosition(status.positionMillis);
      setDuration(status.durationMillis);
      if (status.didJustFinish) {
        setIsPlaying(false);
        // Optionally, auto-play next song here.
      }
    }
  };

  const handlePlayPause = async () => {
    if (!currentSong) return;

    try {
      if (playbackInstance === null) {
        const { sound } = await Audio.Sound.createAsync(
          { uri: currentSong.uri },
          { shouldPlay: true },
          onPlaybackStatusUpdate
        );
        setPlaybackInstance(sound);
        setIsPlaying(true);
      } else {
        if (isPlaying) {
          await playbackInstance.pauseAsync();
          setIsPlaying(false);
        } else {
          await playbackInstance.playAsync();
          setIsPlaying(true);
        }
      }
    } catch (error) {
      console.log('Error playing audio:', error);
    }
  };

  const handleSongSelect = async (song) => {
    try {
      if (playbackInstance) {
        await playbackInstance.unloadAsync();
      }
    } catch (error) {
      console.log('Error unloading audio:', error);
    }
    setCurrentSong(song);
    setPlaybackInstance(null);
    setIsPlaying(false);
    setPosition(0);
    setDuration(0);
    setTimeout(() => {
      handlePlayPause();
    }, 500);
  };

  const formatTime = (milliseconds) => {
    if (!milliseconds) return '0:00';
    const minutes = Math.floor(milliseconds / 60000);
    const seconds = Math.floor((milliseconds % 60000) / 1000);
    return `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
  };

  const changeTheme = () => {
    const themeKeys = Object.keys(themes);
    const currentIndex = themeKeys.indexOf(currentTheme);
    const nextIndex = (currentIndex + 1) % themeKeys.length;
    setCurrentTheme(themeKeys[nextIndex]);
  };

  const renderSongItem = ({ item }) => (
    <TouchableOpacity
      style={[styles.songItem, currentSong?.id === item.id && styles.activeSongItem]}
      onPress={() => handleSongSelect(item)}
    >
      <View style={styles.songItemContent}>
        <View style={[styles.songItemIcon, { backgroundColor: themes[currentTheme].primary }]}>
          <MaterialIcons name="music-note" size={24} color="#FFF" />
        </View>
        <View style={styles.songItemInfo}>
          <Text style={styles.songItemTitle} numberOfLines={1}>
            {item.filename}
          </Text>
          <Text style={styles.songItemDuration}>
            {item.duration ? formatTime(item.duration) : '0:00'}
          </Text>
        </View>
      </View>
    </TouchableOpacity>
  );

  return (
    <LinearGradient colors={themes[currentTheme].gradient} style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={changeTheme}>
          <MaterialIcons name="color-lens" size={28} color="#FFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>My Music</Text>
        <TouchableOpacity>
          <MaterialIcons name="search" size={28} color="#FFF" />
        </TouchableOpacity>
      </View>

      {currentSong && (
        <View style={styles.playerContainer}>
          <Animated.View style={[styles.albumArtContainer, { transform: [{ rotate: spin }] }]}>
            <Image
              source={{
                uri: `https://api.a0.dev/assets/image?text=abstract%20album%20art%20${currentSong.filename}&aspect=1:1`,
              }}
              style={styles.albumArt}
            />
          </Animated.View>

          <View style={styles.songInfo}>
            <Text style={styles.songTitle} numberOfLines={1}>
              {currentSong.filename}
            </Text>
            <Text style={styles.songDuration}>
              {formatTime(position)} / {formatTime(duration)}
            </Text>
          </View>

          <Slider
            style={styles.progressBar}
            value={position}
            maximumValue={duration || 1}
            minimumTrackTintColor={themes[currentTheme].primary}
            maximumTrackTintColor="#555"
            thumbTintColor={themes[currentTheme].primary}
            onValueChange={(value) => setPosition(value)}
            onSlidingComplete={async (value) => {
              if (playbackInstance) {
                await playbackInstance.setPositionAsync(value);
              }
            }}
          />

          <View style={styles.controls}>
            <TouchableOpacity>
              <MaterialIcons name="skip-previous" size={40} color="#FFF" />
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.playButton, { backgroundColor: themes[currentTheme].primary }]}
              onPress={handlePlayPause}
            >
              <MaterialIcons name={isPlaying ? 'pause' : 'play-arrow'} size={48} color="#FFF" />
            </TouchableOpacity>
            <TouchableOpacity>
              <MaterialIcons name="skip-next" size={40} color="#FFF" />
            </TouchableOpacity>
          </View>
        </View>
      )}

      <View style={styles.listContainer}>
        <Text style={styles.listTitle}>Songs</Text>
        <FlatList
          data={songs}
          renderItem={renderSongItem}
          keyExtractor={(item) => item.id}
          showsVerticalScrollIndicator={false}
        />
      </View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    paddingTop: 50,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFF',
  },
  playerContainer: {
    alignItems: 'center',
    padding: 20,
  },
  albumArtContainer: {
    width: width * 0.6,
    height: width * 0.6,
    borderRadius: width * 0.3,
    elevation: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 5 },
    shadowOpacity: 0.5,
    shadowRadius: 8,
    marginBottom: 20,
  },
  albumArt: {
    width: '100%',
    height: '100%',
    borderRadius: width * 0.3,
  },
  songInfo: {
    alignItems: 'center',
    marginBottom: 20,
  },
  songTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFF',
    marginBottom: 5,
  },
  songDuration: {
    fontSize: 14,
    color: '#AAA',
  },
  progressBar: {
    width: '100%',
    height: 40,
  },
  controls: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
    marginTop: 20,
  },
  playButton: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
    marginHorizontal: 30,
  },
  listContainer: {
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderTopLeftRadius: 30,
    borderTopRightRadius: 30,
    padding: 20,
    marginTop: 20,
  },
  listTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFF',
    marginBottom: 15,
  },
  songItem: {
    marginBottom: 10,
    padding: 10,
    borderRadius: 10,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
  },
  activeSongItem: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
  },
  songItemContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  songItemIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
  },
  songItemInfo: {
    flex: 1,
  },
  songItemTitle: {
    fontSize: 16,
    color: '#FFF',
    marginBottom: 4,
  },
  songItemDuration: {
    fontSize: 12,
    color: '#AAA',
  },
});
