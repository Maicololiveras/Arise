package com.praxis.arise;
import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.content.pm.ServiceInfo;
import android.graphics.PixelFormat;
import android.os.*;
import android.provider.Settings;
import android.view.*;
import android.webkit.WebView;
import android.widget.*;
import ai.picovoice.porcupine.PorcupineManager;
import java.io.File;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class WakeService extends Service {
    static final String START="com.praxis.arise.START", STOP="com.praxis.arise.STOP";
    static volatile boolean listeningNow;
    private final WakeState state=new WakeState();
    private final Handler ui=new Handler(Looper.getMainLooper());
    private final ExecutorService engineThread=Executors.newSingleThreadExecutor();
    private PorcupineManager engine;
    private WindowManager windows;
    private LinearLayout panel;
    private Button orb;
    private WebView chat;
    private volatile boolean destroyed;
    private boolean starting;
    private int generation;
    private final BroadcastReceiver screen=new BroadcastReceiver() {
        @Override public void onReceive(Context c,Intent i) { hide(); }
    };
    private final Runnable guard=new Runnable() {
        @Override public void run() {
            if(destroyed) return;
            if(!permitted()) { fail("Escucha detenida: permiso revocado. Actívala nuevamente desde ARISE."); return; }
            if(locked()) hide();
            ui.postDelayed(this,1000);
        }
    };
    @Override public void onCreate() {
        super.onCreate(); windows=getSystemService(WindowManager.class);
        NotificationManager nm=getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel("wake","Escucha de oye ARISE",NotificationManager.IMPORTANCE_LOW));
        IntentFilter filter=new IntentFilter(Intent.ACTION_SCREEN_OFF);
        if(Build.VERSION.SDK_INT>=33) registerReceiver(screen,filter,Context.RECEIVER_NOT_EXPORTED);
        else registerReceiver(screen,filter);
    }
    @Override public int onStartCommand(Intent intent,int flags,int startId) {
        if(intent==null || STOP.equals(intent.getAction()) || !START.equals(intent.getAction())) { stopSelf(); return START_NOT_STICKY; }
        if(starting || state.listening) return START_NOT_STICKY;
        if(!permitted()) { fail("Faltan permisos de micrófono, notificaciones o superposición."); return START_NOT_STICKY; }
        try {
            Notification n=notification("Preparando detector local…");
            if(Build.VERSION.SDK_INT>=30) startForeground(42,n,ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE);
            else startForeground(42,n);
            starting=true; final int epoch=++generation;
            final String key=KeyStoreSecret.read(this);
            final String origin=Origin.validate(getSharedPreferences("wake",0).getString("origin",""));
            engineThread.execute(()->{
                PorcupineManager made=null;
                try {
                    made=new PorcupineManager.Builder().setAccessKey(key)
                            .setKeywordPath(new File(getFilesDir(),"keyword.ppn").getAbsolutePath())
                            .setModelPath(new File(getFilesDir(),"spanish.pv").getAbsolutePath())
                            .setSensitivity(0.5f)
                            .setErrorCallback(error->ui.post(()->{ if(!destroyed && epoch==generation) fail("Detector detenido por un error de audio. Revisa micrófono y modelo."); }))
                            .build(getApplicationContext(),index->ui.post(()->{ if(!destroyed && epoch==generation) detected(origin); }));
                    PorcupineManager ready=made;
                    ui.post(()->{
                        if(destroyed || epoch!=generation) { release(ready); return; }
                        engine=ready;
                        try {
                            if(!permitted()) throw new IllegalStateException();
                            engine.start(); state.start(true,true,true,true); listeningNow=true; starting=false;
                            status("Escuchando ‘oye ARISE’ · detector local");
                            getSystemService(NotificationManager.class).notify(42,notification("Escuchando ‘oye ARISE’ · toca para configurar"));
                            ui.post(guard);
                        } catch(Exception e) { fail("No se pudo abrir el micrófono. Escucha apagada."); }
                    });
                } catch(Exception e) {
                    if(made!=null) release(made);
                    ui.post(()->{if(!destroyed && epoch==generation)fail("No se pudo cargar el detector. Revisa AccessKey, modelo Android y español de la misma versión.");});
                }
            });
        } catch(Exception e) { fail("Android no permitió iniciar la escucha. Abre ARISE y actívala allí."); }
        return START_NOT_STICKY;
    }
    private boolean permitted() {
        return Settings.canDrawOverlays(this) && checkSelfPermission(Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED
                && getSystemService(NotificationManager.class).areNotificationsEnabled();
    }
    private boolean locked() {
        return getSystemService(KeyguardManager.class).isKeyguardLocked() || !getSystemService(PowerManager.class).isInteractive();
    }
    private void detected(String origin) {
        if(!permitted()) { fail("Permiso revocado. Escucha apagada."); return; }
        if(!state.detected(!locked())) return;
        try {
            if(panel==null) createPanel(origin);
            if(panel.getParent()!=null) return;
            ((Button)((LinearLayout)panel.getChildAt(1)).getChildAt(0)).setText("Expandir");
            windows.addView(panel,panelParams(false));
            WindowManager.LayoutParams p=new WindowManager.LayoutParams(dp(56),dp(56),WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                    WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,PixelFormat.TRANSLUCENT);
            p.gravity=Gravity.TOP|Gravity.END;p.y=dp(40);p.x=dp(12);
            windows.addView(orb,p);
        } catch(RuntimeException e) { fail("No se pudo mostrar la burbuja. Revisa el permiso de superposición."); }
    }
    private void createPanel(String origin) {
        panel=new LinearLayout(this);panel.setOrientation(LinearLayout.VERTICAL);panel.setBackgroundColor(0xff101b2d);panel.setPadding(dp(8),dp(6),dp(8),dp(6));
        TextView title=new TextView(this);title.setText("ARISE · Mensajes del PC");title.setTextColor(0xffffffff);title.setTextSize(18);panel.addView(title);
        LinearLayout controls=new LinearLayout(this);panel.addView(controls);
        Button expand=button("Expandir",v->{
            boolean full=state.panel!=WakeState.Panel.EXPANDED;
            if(full)state.expand();else state.panel=WakeState.Panel.COMPACT;
            windows.updateViewLayout(panel,panelParams(full)); ((Button)v).setText(full?"Reducir":"Expandir");
        });controls.addView(expand,new LinearLayout.LayoutParams(0,-2,1));
        controls.addView(button("Ocultar",v->hide()),new LinearLayout.LayoutParams(0,-2,1));
        controls.addView(button("Mic. OFF",v->{status("Escucha apagada por el usuario");stopSelf();}),new LinearLayout.LayoutParams(0,-2,1));
        chat=CompanionView.create(this,origin);panel.addView(chat,new LinearLayout.LayoutParams(-1,0,1));
        orb=button("ARISE",v->hide());orb.setTextSize(9);orb.setTextColor(0xffedfaff);orb.setPadding(0,0,0,0);orb.setBackgroundResource(com.praxis.arise.R.drawable.orb);orb.setContentDescription("ARISE: ocultar panel sin apagar escucha");
    }
    private WindowManager.LayoutParams panelParams(boolean expanded) {
        int height=getResources().getDisplayMetrics().heightPixels;
        WindowManager.LayoutParams p=new WindowManager.LayoutParams(-1,(int)(height*(expanded?0.85:0.48)),
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL|WindowManager.LayoutParams.FLAG_SECURE,
                PixelFormat.TRANSLUCENT);
        p.gravity=Gravity.BOTTOM;p.softInputMode=WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE;return p;
    }
    private void hide() {
        state.hide();
        if(panel!=null && panel.getParent()!=null) windows.removeView(panel);
        if(orb!=null && orb.getParent()!=null) windows.removeView(orb);
    }
    private Notification notification(String text) {
        PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        PendingIntent stop=PendingIntent.getService(this,1,new Intent(this,WakeService.class).setAction(STOP),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        return new Notification.Builder(this,"wake").setSmallIcon(com.praxis.arise.R.drawable.orb).setContentTitle("ARISE · Micrófono activo")
                .setContentText(text).setContentIntent(open).setOngoing(true).setVisibility(Notification.VISIBILITY_PRIVATE)
                .addAction(new Notification.Action.Builder(null,"Apagar micrófono",stop).build()).build();
    }
    private Button button(String text,View.OnClickListener listener) { Button b=new Button(this);b.setText(text);b.setTextSize(12);b.setOnClickListener(listener);return b; }
    private int dp(int n) { return Math.round(n*getResources().getDisplayMetrics().density); }
    private void status(String value) { getSharedPreferences("wake",0).edit().putString("status",value).apply(); }
    private void fail(String value) { status(value); state.stop(); stopSelf(); }
    private static void release(PorcupineManager instance) { try { instance.stop(); } catch(Exception ignored) {} instance.delete(); }
    @Override public void onDestroy() {
        destroyed=true;listeningNow=false;++generation;state.stop();hide();ui.removeCallbacks(guard);
        unregisterReceiver(screen);
        if(engine!=null) { release(engine);engine=null; }
        engineThread.shutdown();
        if(chat!=null)chat.destroy();
        stopForeground(STOP_FOREGROUND_REMOVE);
        if(getSharedPreferences("wake",0).getString("status","").startsWith("Escuchando"))status("Escucha apagada");
        super.onDestroy();
    }
    @Override public IBinder onBind(Intent i) { return null; }
}
