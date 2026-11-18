import {useLayoutEffect, useState} from 'react';
import {useApp} from '../context.jsx';
import '../pages/catalog-entrance.css';

export function useGridEntrance(ready = true) {
  const {route, claimGridEntrance} = useApp();
  const [animate, setAnimate] = useState(false);

  useLayoutEffect(() => {
    if (ready && claimGridEntrance(route)) setAnimate(true);
  }, [ready, route, claimGridEntrance]);

  return [animate, () => setAnimate(false)];
}
