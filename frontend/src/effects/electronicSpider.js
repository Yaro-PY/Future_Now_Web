// Adapted from the user-provided ElectronicSpider/script.js.
// Keep its inverse-kinematics tentacles, with one managed animation loop.
export function startElectronicSpider(canvas,{hue=215,color='#2563eb',followPointer=false}={}) {
  const context=canvas.getContext('2d');
  if(!context) return {destroy(){},setPaused(){}};
  const area=canvas.parentElement;
  const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
  let width=0,height=0,legs=[],frame=0,previousTime=0,lastPaint=0,phase=2.25;
  let stopped=false,paused=false,visible=true;
  const target={x:0,y:0},lastTarget={x:0,y:0};
  let pointer=null;
  const distance=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
  const clamp=(value,low,high)=>Math.min(high,Math.max(low,value));

  class Segment {
    constructor(parent,length,first) {
      this.position={...(first?parent:parent.next)};
      this.length=length;
      this.angle=0;
      this.next={x:this.position.x+length,y:this.position.y};
    }
    update(point) {
      this.angle=Math.atan2(point.y-this.position.y,point.x-this.position.x);
      this.position.x=point.x-this.length*Math.cos(this.angle);
      this.position.y=point.y-this.length*Math.sin(this.angle);
      this.next.x=point.x;
      this.next.y=point.y;
    }
    anchor(point) {
      this.position.x=point.x;
      this.position.y=point.y;
      this.next.x=point.x+this.length*Math.cos(this.angle);
      this.next.y=point.y+this.length*Math.sin(this.angle);
    }
  }

  class Tentacle {
    constructor(x,y,length,count) {
      this.x=x;this.y=y;this.length=length;this.random=Math.random();
      this.color=`hsl(${this.random*20+hue} 92% ${this.random*12+44}%)`;
      this.segments=[new Segment(this,length/count,true)];
      for(let i=1;i<count;i++) this.segments.push(new Segment(this.segments[i-1],length/count,false));
    }
    move(speed) {
      const angle=Math.atan2(target.y-this.y,target.x-this.x);
      const tip={x:target.x-.8*(speed+5)*Math.cos(angle),y:target.y-.8*(speed+5)*Math.sin(angle)};
      this.segments.at(-1).update(tip);
      for(let i=this.segments.length-2;i>=0;i--) this.segments[i].update(this.segments[i+1].position);
      if(distance(this,target)<=this.length+speed) {
        this.segments[0].anchor(this);
        for(let i=1;i<this.segments.length;i++) this.segments[i].anchor(this.segments[i-1].next);
      }
    }
    show() {
      context.beginPath();
      context.moveTo(this.x,this.y);
      for(const segment of this.segments) context.lineTo(segment.next.x,segment.next.y);
      context.strokeStyle=this.color;
      context.lineWidth=.45+this.random*1.15;
      context.stroke();
      context.beginPath();
      context.arc(this.x,this.y,1+this.random*2,0,Math.PI*2);
      context.fillStyle=this.color;
      context.fill();
    }
  }

  function paint() {
    context.clearRect(0,0,width,height);
    context.lineCap='round';context.lineJoin='round';
    const speed=distance(lastTarget,target);
    for(const leg of legs) {
      if(distance(leg,target)>leg.length) continue;
      leg.move(speed);leg.show();
    }
    context.beginPath();
    context.arc(target.x,target.y,Math.min(12,speed+5),0,Math.PI*2);
    context.fillStyle=color;
    context.fill();
    lastTarget.x=target.x;lastTarget.y=target.y;
  }

  function patrolDestination() {
    return {
      x:width*(.5+.34*Math.sin(phase)),
      y:height*(.5+.37*Math.cos(phase*1.45)),
    };
  }

  function resize() {
    const nextWidth=canvas.clientWidth,nextHeight=canvas.clientHeight;
    if(!nextWidth||!nextHeight) return;
    const initial=width===0;
    if(!initial) {
      target.x*=nextWidth/width;
      target.y*=nextHeight/height;
    }
    width=nextWidth;height=nextHeight;pointer=null;
    const ratio=Math.min(window.devicePixelRatio||1,1.75);
    canvas.width=Math.round(width*ratio);canvas.height=Math.round(height*ratio);
    context.setTransform(ratio,0,0,ratio,0,0);
    const count=clamp(Math.round(width*height/1350),65,230);
    const maxLength=clamp(Math.min(width,height)*.49,18,190);
    const minLength=Math.min(42,maxLength*.65);
    legs=Array.from({length:count},()=>new Tentacle(Math.random()*width,Math.random()*height,
      Math.random()*(maxLength-minLength)+minLength,18));
    if(initial) Object.assign(target,patrolDestination());
    Object.assign(lastTarget,target);
    paint();
  }

  function animate(time) {
    frame=0;
    if(stopped||paused||!visible||document.hidden||motion.matches) return;
    const interval=1000/45;
    if(time-lastPaint>=interval) {
      const elapsed=Math.min((time-(previousTime||time-interval))/1000,.05);
      previousTime=time;lastPaint=time;
      const chasing=followPointer&&pointer;
      if(!chasing) phase+=elapsed*.8;
      const destination=chasing||patrolDestination();
      const blend=1-Math.exp(-elapsed*(chasing?9:4));
      target.x+=(clamp(destination.x,12,width-12)-target.x)*blend;
      target.y+=(clamp(destination.y,12,height-12)-target.y)*blend;
      paint();
    }
    frame=requestAnimationFrame(animate);
  }

  function syncAnimation() {
    if(frame) cancelAnimationFrame(frame);
    frame=0;previousTime=0;lastPaint=0;
    if(!document.hidden&&visible&&!motion.matches&&!stopped&&!paused) frame=requestAnimationFrame(animate);
  }

  function onPointer(event) {
    if(event.pointerType==='touch'||motion.matches||paused) return;
    const bounds=canvas.getBoundingClientRect();
    if(bounds.width&&bounds.height) {
      pointer={
        x:(event.clientX-bounds.left)*width/bounds.width,
        y:(event.clientY-bounds.top)*height/bounds.height,
      };
    }
  }

  function clearPointer() {pointer=null;}

  const resizeObserver=new ResizeObserver(resize);
  const visibilityObserver=new IntersectionObserver(([entry])=>{
    visible=entry.isIntersecting;
    if(!visible) clearPointer();
    syncAnimation();
  });
  resize();syncAnimation();
  resizeObserver.observe(canvas);
  visibilityObserver.observe(canvas);
  if(followPointer) {
    area.addEventListener('pointermove',onPointer,{passive:true});
    area.addEventListener('pointerleave',clearPointer);
    area.addEventListener('pointercancel',clearPointer);
  }
  window.addEventListener('blur',clearPointer);
  document.addEventListener('visibilitychange',syncAnimation);
  motion.addEventListener('change',syncAnimation);

  function destroy() {
    stopped=true;
    if(frame) cancelAnimationFrame(frame);
    resizeObserver.disconnect();
    visibilityObserver.disconnect();
    area.removeEventListener('pointermove',onPointer);
    area.removeEventListener('pointerleave',clearPointer);
    area.removeEventListener('pointercancel',clearPointer);
    window.removeEventListener('blur',clearPointer);
    document.removeEventListener('visibilitychange',syncAnimation);
    motion.removeEventListener('change',syncAnimation);
  }

  return {destroy,setPaused(value){paused=value;if(paused)clearPointer();syncAnimation();}};
}
