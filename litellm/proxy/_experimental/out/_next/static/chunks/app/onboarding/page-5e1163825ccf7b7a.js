(self.webpackChunk_N_E=self.webpackChunk_N_E||[]).push([[461],{61994:function(e,s,t){Promise.resolve().then(t.bind(t,667))},667:function(e,s,t){"use strict";t.r(s),t.d(s,{default:function(){return g}});var l=t(3827),n=t(64090),a=t(47907),i=t(16450),r=t(18190),o=t(13810),c=t(10384),u=t(46453),d=t(71801),m=t(52273),h=t(42440),x=t(30953),f=t(777),p=t(37963),j=t(60620),_=t(1861);function g(){let[e]=j.Z.useForm(),s=(0,a.useSearchParams)();!function(e){console.log("COOKIES",document.cookie);let s=document.cookie.split("; ").find(s=>s.startsWith(e+"="));s&&s.split("=")[1]}("token");let t=s.get("invitation_id"),[g,Z]=(0,n.useState)(null),[k,w]=(0,n.useState)(""),[S,b]=(0,n.useState)(""),[N,v]=(0,n.useState)(null),[y,E]=(0,n.useState)(""),[I,O]=(0,n.useState)("");return(0,n.useEffect)(()=>{t&&(0,f.W_)(t).then(e=>{let s=e.login_url;console.log("login_url:",s),E(s);let t=e.token,l=(0,p.o)(t);O(t),console.log("decoded:",l),Z(l.key),console.log("decoded user email:",l.user_email),b(l.user_email),v(l.user_id)})},[t]),(0,l.jsx)("div",{className:"mx-auto w-full max-w-md mt-10",children:(0,l.jsxs)(o.Z,{children:[(0,l.jsx)(h.Z,{className:"text-sm mb-5 text-center",children:"\uD83D\uDE85 LiteLLM"}),(0,l.jsx)(h.Z,{className:"text-xl",children:"Sign up"}),(0,l.jsx)(d.Z,{children:"Claim your user account to login to Admin UI."}),(0,l.jsx)(r.Z,{className:"mt-4",title:"SSO",icon:x.GH$,color:"sky",children:(0,l.jsxs)(u.Z,{numItems:2,className:"flex justify-between items-center",children:[(0,l.jsx)(c.Z,{children:"SSO is under the Enterprise Tirer."}),(0,l.jsx)(c.Z,{children:(0,l.jsx)(i.Z,{variant:"primary",className:"mb-2",children:(0,l.jsx)("a",{href:"https://forms.gle/W3U4PZpJGFHWtHyA9",target:"_blank",children:"Get Free Trial"})})})]})}),(0,l.jsxs)(j.Z,{className:"mt-10 mb-5 mx-auto",layout:"vertical",onFinish:e=>{console.log("in handle submit. accessToken:",g,"token:",I,"formValues:",e),g&&I&&(e.user_email=S,N&&t&&(0,f.m_)(g,t,N,e.password).then(e=>{var s;let t="/ui/";t+="?userID="+((null===(s=e.data)||void 0===s?void 0:s.user_id)||e.user_id),document.cookie="token="+I,console.log("redirecting to:",t),window.location.href=t}))},children:[(0,l.jsxs)(l.Fragment,{children:[(0,l.jsx)(j.Z.Item,{label:"Email Address",name:"user_email",children:(0,l.jsx)(m.Z,{type:"email",disabled:!0,value:S,defaultValue:S,className:"max-w-md"})}),(0,l.jsx)(j.Z.Item,{label:"Password",name:"password",rules:[{required:!0,message:"password required to sign up"}],help:"Create a password for your account",children:(0,l.jsx)(m.Z,{placeholder:"",type:"password",className:"max-w-md"})})]}),(0,l.jsx)("div",{className:"mt-10",children:(0,l.jsx)(_.ZP,{htmlType:"submit",children:"Sign Up"})})]})]})})}}},function(e){e.O(0,[665,294,684,777,971,69,744],function(){return e(e.s=61994)}),_N_E=e.O()}]);