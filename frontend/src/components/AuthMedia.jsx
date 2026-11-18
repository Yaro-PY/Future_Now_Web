import {useCallback,useEffect,useRef,useState} from 'react';
import {useApp} from '../context.jsx';
import './auth-media.css';

const folder='/assets/media/auth/';
const soundPreferenceKey = 'future-now.intro-sound';

function soundEnabledByDefault() {
  try {
    return localStorage.getItem(soundPreferenceKey) !== 'off';
  } catch {
    return true;
  }
}

export function useAuthMedia(){
  const video=useRef(null),audio=useRef(null),alive=useRef(true),wantVideo=useRef(!window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const [sound,setSound]=useState(soundEnabledByDefault);
  const wantSound=useRef(sound);
  const [playing,setPlaying]=useState(wantVideo.current),[soundFailed,setSoundFailed]=useState(false),[videoFailed,setVideoFailed]=useState(false);

  const playSound = useCallback(() => {
    const music = audio.current;
    if (!wantSound.current || document.hidden || !music?.paused || music.error) return;
    // Autoplay can be rejected before user activation. Keep the preference and retry on interaction.
    music.play().catch(() => {});
  }, []);
  useEffect(()=>{
    alive.current=true;
    const film=video.current,music=audio.current,preference=window.matchMedia('(prefers-reduced-motion: reduce)');
    music.volume=.35;
    const videoError=()=>{if(alive.current){wantVideo.current=false;setPlaying(false);setVideoFailed(true);}};
    const audioError=()=>{if(alive.current)setSoundFailed(true);};
    film.addEventListener('error',videoError);music.addEventListener('error',audioError);
    if(film.error)videoError();if(music.error)audioError();
    const sync=()=>{
      if(document.hidden){film.pause();music.pause();return;}
      if(wantVideo.current)film.play().catch(()=>{if(alive.current&&!document.hidden&&wantVideo.current){wantVideo.current=false;setPlaying(false);}});
      playSound();
    };
    const reduce=event=>{if(event.matches){wantVideo.current=false;film.pause();setPlaying(false);}};
    const startOnInteraction = event => {
      if (!event.isTrusted || event.target.closest?.('[data-action=auth-sound]')) return;
      playSound();
    };
    document.addEventListener('click',startOnInteraction,true);
    document.addEventListener('keydown',startOnInteraction,true);
    document.addEventListener('visibilitychange',sync);preference.addEventListener('change',reduce);sync();
    return ()=>{
      alive.current=false;film.removeEventListener('error',videoError);music.removeEventListener('error',audioError);document.removeEventListener('visibilitychange',sync);preference.removeEventListener('change',reduce);
      document.removeEventListener('click',startOnInteraction,true);
      document.removeEventListener('keydown',startOnInteraction,true);
      film.pause();music.pause();film.removeAttribute('src');music.removeAttribute('src');film.load();music.load();
    };
  },[playSound]);
  function toggleSound(){
    const enabled = !wantSound.current;
    wantSound.current = enabled;
    setSound(enabled);
    try {
      localStorage.setItem(soundPreferenceKey, enabled ? 'on' : 'off');
    } catch {
      // The button continues to work when browser storage is unavailable.
    }
    if (enabled) playSound();
    else audio.current.pause();
  }
  async function toggleVideo(){
    if(wantVideo.current){wantVideo.current=false;video.current.pause();setPlaying(false);return;}
    try{await video.current.play();if(alive.current){wantVideo.current=true;setPlaying(true);}}
    catch{if(alive.current)setPlaying(false);}
  }
  return {video,audio,sound,playing,soundFailed,videoFailed,toggleSound,toggleVideo,
    onAudioError:()=>setSoundFailed(true),
    onVideoError:()=>{wantVideo.current=false;setPlaying(false);setVideoFailed(true);}};
}
export function AuthMedia({media}){
  return <div className="auth-media" aria-hidden="true">
    <img className="auth-background" src={folder+'lusion-poster.jpg'} alt="" fetchPriority="high"/>
    <video className="auth-background auth-video" ref={media.video} src={folder+'lusion-background.mp4'} poster={folder+'lusion-poster.jpg'} muted loop playsInline preload="metadata" tabIndex={-1} hidden={media.videoFailed} onError={media.onVideoError}/>
    <audio ref={media.audio} src={folder+'cash_cash_ft_tritonal_-_untouchable_extended_mix.mp3'} loop preload="none" onError={media.onAudioError}/>
  </div>;
}
export function AuthMediaControls({media}){
  const {t}=useApp();
  return <div className="auth-media-controls">
    <button type="button" data-action="auth-sound" aria-label={t(media.soundFailed?'introSoundUnavailable':media.sound?'introSoundOff':'introSoundOn')} title={t(media.sound?'introSoundOff':'introSoundOn')} aria-pressed={media.sound} disabled={media.soundFailed} onClick={media.toggleSound}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="M11 5 6 9H3v6h3l5 4Z"/>{media.sound?<><path d="M15 8a6 6 0 0 1 0 8M18 5a10 10 0 0 1 0 14"/></>:<path d="m16 9 6 6m0-6-6 6"/>}</svg>
    </button>
    <button type="button" data-action="auth-video" aria-label={t(media.videoFailed?'introVideoUnavailable':media.playing?'introVideoPause':'introVideoPlay')} title={t(media.playing?'introVideoPause':'introVideoPlay')} aria-pressed={media.playing} disabled={media.videoFailed} onClick={media.toggleVideo}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">{media.playing?<path d="M8 5v14M16 5v14"/>:<path d="m8 5 11 7-11 7Z"/>}</svg>
    </button>
  </div>;
}
