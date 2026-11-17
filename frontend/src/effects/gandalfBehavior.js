// A quiet guide: keep clear of the pointer, wander, then take a short rest.
export function gandalfDestination({time,phase,width,height,pointer,target}){
  if(time-pointer.at<1600)return {state:'guide',x:pointer.x+(pointer.x>width*.7?-64:64),y:pointer.y-40};
  if(Math.floor(time/1000)%24>=20&&Math.floor(time/1000)%24<22)return {state:'rest',...target};
  const sine=Math.sin(phase),denominator=1+sine*sine;
  return {state:'wander',x:width/2+(width*.39*Math.cos(phase))/denominator,
    y:height/2+(height*.64*Math.cos(phase)*sine)/denominator};
}
