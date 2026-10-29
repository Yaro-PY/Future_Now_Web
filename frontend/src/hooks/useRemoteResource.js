import {useCallback, useEffect, useRef, useState} from 'react';

// Responses from a previous route or filter set cannot replace the current screen.
export function useRemoteResource({enabled, resourceKey, load, onLoad, onError}) {
  const callbacks = useRef({load,onLoad,onError});
  callbacks.current = {load,onLoad,onError};
  const [state, setState] = useState({data:null,error:false});
  useEffect(() => {
    let active = true;
    setState({data:null,error:false});
    if (!enabled) return () => { active = false; };
    const request = callbacks.current.load;
    Promise.resolve().then(request).then(data => {
      if (!active) return;
      setState({data,error:false}); callbacks.current.onLoad?.(data);
    }).catch(error => {
      if (!active) return;
      setState({data:null,error:true}); callbacks.current.onError?.(error);
    });
    return () => { active = false; };
  }, [enabled,resourceKey]);
  const setData = useCallback(update => setState(current => ({data:typeof update === 'function' ? update(current.data) : update,error:false})), []);
  return {data:state.data,error:state.error,setData};
}
