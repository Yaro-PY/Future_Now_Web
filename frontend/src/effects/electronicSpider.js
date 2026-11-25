// Adapted from the user-provided ElectronicSpider/script.js.
// Keep its inverse-kinematics tentacles, with one managed animation loop.
export function startElectronicSpider(canvas,{hue=215,color='#2563eb',roaming=false}={}) {
  const context=canvas.getContext('2d');
  if(!context) return {destroy(){},setPaused(){}};
  const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
  const scale=.605;
  const edge=12;
  let width=0,height=0,legs=[],frame=0,previousTime=0,lastPaint=0,phase=roaming?2.25:0;
  let stopped=false,paused=false,visible=true;
  const target={x:0,y:0},lastTarget={x:0,y:0};
  let cursor=null,pointer=null,verticalInset=edge;
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
      const tip={x:target.x-.8*(speed+5*scale)*Math.cos(angle),y:target.y-.8*(speed+5*scale)*Math.sin(angle)};
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
      context.lineWidth=(.45+this.random*1.15)*scale;
      context.stroke();
      context.beginPath();
      context.arc(this.x,this.y,(1+this.random*2)*scale,0,Math.PI*2);
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
    context.arc(target.x,target.y,Math.min(12*scale,speed+5*scale),0,Math.PI*2);
    context.fillStyle=color;
    context.fill();
    lastTarget.x=target.x;lastTarget.y=target.y;
  }

  function patrolDestination() {
    if(!roaming) return {x:width/2,y:verticalInset+(height-2*verticalInset)*(1-Math.cos(phase))/2};
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
    width=nextWidth;height=nextHeight;
    const ratio=Math.min(window.devicePixelRatio||1,1.75);
    canvas.width=Math.round(width*ratio);canvas.height=Math.round(height*ratio);
    context.setTransform(ratio,0,0,ratio,0,0);
    const count=clamp(Math.round(width*height/1350),65,roaming?360:230);
    const span=roaming?Math.min(width,height)*.49:width*.98;
    const maxLength=clamp(span,18,roaming?270:190)*scale;
    const minLength=Math.min(42*scale,maxLength*.65);
    verticalInset=Math.min(height/2,roaming ? edge : maxLength+edge);
    legs=Array.from({length:count},()=>new Tentacle(Math.random()*width,Math.random()*height,
      Math.random()*(maxLength-minLength)+minLength,18));
    if(initial) Object.assign(target,patrolDestination());
    target.y=clamp(target.y,verticalInset,height-verticalInset);
    updatePointer();
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
      const chasing=pointer;
      if(!chasing) phase+=elapsed*(roaming ? .8 : .48);
      const destination=chasing||patrolDestination();
      const blend=1-Math.exp(-elapsed*(chasing?9:4));
      const horizontalInset=Math.min(edge,width/2);
      target.x+=(clamp(destination.x,horizontalInset,width-horizontalInset)-target.x)*blend;
      target.y+=(clamp(destination.y,verticalInset,height-verticalInset)-target.y)*blend;
      paint();
    }
    frame=requestAnimationFrame(animate);
  }

  function syncAnimation() {
    if(frame) cancelAnimationFrame(frame);
    frame=0;previousTime=0;lastPaint=0;
    if(!document.hidden&&visible&&!motion.matches&&!stopped&&!paused) frame=requestAnimationFrame(animate);
  }

  function updatePointer() {
    pointer=null;
    if(!cursor) return;
    const bounds=canvas.getBoundingClientRect();
    const x=cursor.x-bounds.left,y=cursor.y-bounds.top;
    if(x>=0&&x<bounds.width&&y>=0&&y<bounds.height) {
      pointer={x:x*width/bounds.width,y:y*height/bounds.height};
    }
  }

  function onPointer(event) {
    if(event.pointerType==='touch') {clearPointer();return;}
    if(motion.matches||paused) return;
    cursor={x:event.clientX,y:event.clientY};
    updatePointer();
  }

  function clearPointer() {cursor=null;pointer=null;}
  function onPointerOut(event) {if(!event.relatedTarget) clearPointer();}

  const resizeObserver=new ResizeObserver(resize);
  const visibilityObserver=new IntersectionObserver(([entry])=>{
    visible=entry.isIntersecting;
    if(!visible) clearPointer();
    syncAnimation();
  });
  resize();syncAnimation();
  resizeObserver.observe(canvas);
  visibilityObserver.observe(canvas);
  // Observe the pointer without taking control away from the page underneath.
  window.addEventListener('pointermove',onPointer,{capture:true,passive:true});
  window.addEventListener('pointerout',onPointerOut,true);
  window.addEventListener('pointercancel',clearPointer,true);
  window.addEventListener('blur',clearPointer);
  document.addEventListener('visibilitychange',syncAnimation);
  motion.addEventListener('change',syncAnimation);

  function destroy() {
    stopped=true;
    if(frame) cancelAnimationFrame(frame);
    resizeObserver.disconnect();
    visibilityObserver.disconnect();
    window.removeEventListener('pointermove',onPointer,true);
    window.removeEventListener('pointerout',onPointerOut,true);
    window.removeEventListener('pointercancel',clearPointer,true);
    window.removeEventListener('blur',clearPointer);
    document.removeEventListener('visibilitychange',syncAnimation);
    motion.removeEventListener('change',syncAnimation);
  }

  return {destroy,setPaused(value){paused=value;if(paused)clearPointer();syncAnimation();}};
}
