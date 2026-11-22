export function isSpiderPixel(canvas,x,y,padding=3) {
  const bounds=canvas.getBoundingClientRect();
  if(!bounds.width||!bounds.height||x<bounds.left||x>=bounds.right||y<bounds.top||y>=bounds.bottom) return false;
  const scaleX=canvas.width/bounds.width,scaleY=canvas.height/bounds.height;
  const left=Math.max(0,Math.floor((x-bounds.left-padding)*scaleX));
  const top=Math.max(0,Math.floor((y-bounds.top-padding)*scaleY));
  const right=Math.min(canvas.width,Math.ceil((x-bounds.left+padding+1)*scaleX));
  const bottom=Math.min(canvas.height,Math.ceil((y-bounds.top+padding+1)*scaleY));
  const context=canvas.getContext('2d');
  if(!context) return false;
  const pixels=context.getImageData(left,top,right-left,bottom-top).data;
  for(let i=3;i<pixels.length;i+=4) if(pixels[i]>90) return true;
  return false;
}
