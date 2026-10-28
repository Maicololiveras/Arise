package com.praxis.arise;
import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.*;
import android.provider.Settings;
import android.text.InputType;
import android.view.View;
import android.webkit.WebView;
import android.widget.*;
import java.io.*;
import java.nio.file.*;

public class MainActivity extends Activity {
    private TextView status, updateStatus;
    private boolean updateBusy;
    private AppUpdate availableUpdate;
    private EditText origin, accessKey;
    private WebView chat;
    private boolean foreground;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final Runnable refresh = new Runnable() {
        @Override public void run() {
            if (!foreground) return;
            String message=getSharedPreferences("wake", 0).getString("status", "Escucha apagada");
            if(message.startsWith("Escuchando") && !WakeService.listeningNow) message="Escucha apagada; activa nuevamente para escuchar.";
            if (status != null) status.setText(message
                    + "\nSuperposición: " + (Settings.canDrawOverlays(MainActivity.this) ? "permitida" : "pendiente")
                    + " · Micrófono: " + (checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED ? "permitido" : "pendiente"));
            ui.postDelayed(this, 1000);
        }
    };
    @Override public void onCreate(Bundle state) { super.onCreate(state); setup(); }
    private void setup() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout box = new LinearLayout(this); box.setOrientation(LinearLayout.VERTICAL); box.setPadding(24,24,24,24);
        scroll.addView(box); setContentView(scroll);
        scroll.setOnApplyWindowInsetsListener((v,insets)->{
            if (Build.VERSION.SDK_INT >= 30) {
                android.graphics.Insets bars=insets.getInsets(android.view.WindowInsets.Type.systemBars());
                v.setPadding(bars.left,bars.top,bars.right,bars.bottom);
            } else v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());
            return insets;
        });
        ImageView identity=new ImageView(this); identity.setImageResource(R.drawable.orb);
        identity.setContentDescription("Orbe ARISE");
        int iconSize=(int)(80*getResources().getDisplayMetrics().density);
        box.addView(identity,new LinearLayout.LayoutParams(-1,iconSize));
        label(box, "ARISE Companion · QA", 24);
        updateStatus=label(box,"Versión "+BuildConfig.VERSION_NAME+" · Buscando actualizaciones…",14);
        button(box,"Buscar actualización / ver descarga",v->{
            if(availableUpdate!=null) showUpdate(); else checkUpdate(true);
        });
        checkUpdate(false);
        label(box, "La detección de ‘oye ARISE’ abre el panel. El trabajo sigue en tu PC con los permisos del chat. Ocultar no apaga la escucha; Apagar micrófono sí.", 16);
        status = label(box, "Escucha apagada", 16);
        origin = field(box, "https://tu-pc.tu-red.ts.net", false);
        origin.setText(getSharedPreferences("wake",0).getString("origin", ""));
        button(box, "Guardar conexión y vincular chat", v -> {
            try {
                String host = Origin.validate(origin.getText().toString());
                stopService(new Intent(this, WakeService.class));
                getSharedPreferences("wake",0).edit().putString("origin",host).apply();
                openChat(host);
            } catch (RuntimeException e) { tell("Introduce el origen HTTPS de Tailscale, sin rutas ni puertos."); }
        });
        button(box, "1 · Permitir mostrar sobre otras apps", v -> new AlertDialog.Builder(this)
                .setTitle("Burbuja sobre otras aplicaciones")
                .setMessage("Android abrirá sus ajustes. Activa el permiso de ARISE Companion QA. Puedes revocarlo allí en cualquier momento. Esto no concede control del PC ni acceso al contenido de otras apps.")
                .setNegativeButton("Ahora no",null).setPositiveButton("Abrir ajustes",(d,w)-> {
                    try { startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,Uri.parse("package:"+getPackageName()))); }
                    catch (ActivityNotFoundException e) { tell("Abre Ajustes > Aplicaciones > Acceso especial > Mostrar sobre otras apps."); }
                }).show());
        button(box, "2 · Permitir micrófono y notificaciones", v -> {
            if (Build.VERSION.SDK_INT >= 33) requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO, Manifest.permission.POST_NOTIFICATIONS},10);
            else requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},10);
        });
        label(box,"3 · Detector local Porcupine (opcional)\nRequiere tu AccessKey y modelos compatibles de ‘oye ARISE’ para Android y español. El SDK puede validar la licencia con Picovoice. No se incluyen clave ni modelo personalizado; consulta sus condiciones. Sin configurarlo, el chat manual sigue disponible.",16);
        accessKey = field(box,"AccessKey de Picovoice (no se muestra al volver)",true);
        button(box,"Guardar clave del detector",v->{
            try {
                String key=accessKey.getText().toString().trim();
                if(key.isEmpty()) { tell("Introduce una clave."); return; }
                stopService(new Intent(this,WakeService.class)); KeyStoreSecret.save(this,key); accessKey.setText(""); tell("Clave guardada con Android Keystore.");
            } catch(Exception e) { tell("No se pudo guardar la clave. No se activó la escucha."); }
        });
        button(box,"Importar ‘oye ARISE’ Android (.ppn)",v->pick(20));
        button(box,"Importar modelo de español (.pv)",v->pick(21));
        button(box,"Activar escucha de ‘oye ARISE’",v->startWake());
        button(box,"Apagar micrófono y quitar burbuja",v->{ stopService(new Intent(this,WakeService.class)); tell("Escucha apagada. Las tareas del PC se detienen desde el chat."); });
        button(box,"Borrar clave y modelos locales",v->new AlertDialog.Builder(this).setMessage("Se apagará la escucha y se borrará la configuración del detector. La vinculación del PC se revoca por separado en ARISE.")
                .setNegativeButton("Cancelar",null).setPositiveButton("Borrar",(d,w)->{
                    stopService(new Intent(this,WakeService.class));
                    getSharedPreferences("wake",0).edit().remove("key").apply();
                    new File(getFilesDir(),"keyword.ppn").delete(); new File(getFilesDir(),"spanish.pv").delete(); tell("Detector eliminado.");
                }).show());
        label(box,"La escucha no se reinicia al encender el teléfono ni al volver a dar un permiso. Con pantalla bloqueada no mostramos conversaciones. Pruebas de batería y bloqueo pendientes en Redmi 13C.",14);
    }
    private void checkUpdate(boolean manual) {
        if(updateBusy) return;
        updateBusy=true;
        TextView target=updateStatus;
        target.setText("Versión "+BuildConfig.VERSION_NAME+" · Consultando GitHub…");
        new Thread(()->{
            try {
                AppUpdate update=AppUpdate.fetch();
                runOnUiThread(()->{
                    updateBusy=false;
                    if(isFinishing() || isDestroyed() || target!=updateStatus) return;
                    availableUpdate=update.code>BuildConfig.VERSION_CODE?update:null;
                    target.setText(availableUpdate==null?"Versión "+BuildConfig.VERSION_NAME+" · Sin actualizaciones publicadas":"Disponible "+update.version+" · Pulsa Ver descarga para actualizar");
                    if(manual && availableUpdate!=null) showUpdate();
                });
            } catch(Exception e) {
                runOnUiThread(()->{
                    updateBusy=false;
                    if(!isFinishing() && !isDestroyed() && target==updateStatus)
                        target.setText("Versión "+BuildConfig.VERSION_NAME+" · No se pudo comprobar la actualización. Puedes volver a intentarlo; el chat sigue disponible.");
                });
            }
        },"arise-update-check").start();
    }
    private void showUpdate() {
        AppUpdate update=availableUpdate;
        if(update==null) return;
        new AlertDialog.Builder(this).setTitle("ARISE Android "+update.version)
            .setMessage("Se abrirá GitHub para descargar ARISE-Android-QA.apk. Android te pedirá confirmar la instalación. "
                +"Esta versión QA usa firma de depuración; si Android rechaza la actualización por firma, conserva tu configuración antes de reinstalar. "
                +"No se instalará ni se cambiarán permisos automáticamente.")
            .setNegativeButton("Ahora no",null).setPositiveButton("Abrir descarga",(d,w)->{
                try { startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(update.url))); }
                catch(ActivityNotFoundException e) { tell("No hay navegador disponible para abrir GitHub."); }
            }).show();
    }
    private void startWake() {
        if (!foreground) return;
        if (!Settings.canDrawOverlays(this)) { tell("Falta permitir mostrar sobre otras apps (paso 1)."); return; }
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED
                || !getSystemService(NotificationManager.class).areNotificationsEnabled()) { tell("Permite micrófono y notificaciones (paso 2)."); return; }
        try {
            Origin.validate(getSharedPreferences("wake",0).getString("origin",""));
            if (KeyStoreSecret.read(this).isEmpty() || !new File(getFilesDir(),"keyword.ppn").isFile() || !new File(getFilesDir(),"spanish.pv").isFile()) {
                tell("Configura la clave y ambos modelos del detector. No se sustituirá la frase."); return;
            }
            startForegroundService(new Intent(this,WakeService.class).setAction(WakeService.START));
        } catch(Exception e) { tell("No se pudo activar. Revisa la conexión y el detector."); }
    }
    private void pick(int code) {
        stopService(new Intent(this,WakeService.class));
        startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE),code);
    }
    @Override protected void onActivityResult(int code,int result,Intent data) {
        super.onActivityResult(code,result,data);
        if ((code!=20 && code!=21) || result!=RESULT_OK || data==null || data.getData()==null) return;
        Uri uri=data.getData();
        new Thread(()->{
            File target=new File(getFilesDir(),code==20?"keyword.ppn":"spanish.pv"),temp=new File(getFilesDir(),target.getName()+".tmp");
            try(InputStream in=getContentResolver().openInputStream(uri); OutputStream out=new FileOutputStream(temp)) {
                if(in==null) throw new IOException();
                byte[] b=new byte[8192]; long total=0; int n;
                while((n=in.read(b))!=-1) { total+=n; if(total>32*1024*1024) throw new IOException(); out.write(b,0,n); }
                if(total==0) throw new IOException();
                out.close(); Files.move(temp.toPath(),target.toPath(),StandardCopyOption.REPLACE_EXISTING);
                runOnUiThread(()->tell("Archivo importado. La compatibilidad se comprobará al activar el detector."));
            } catch(Exception e) { temp.delete(); runOnUiThread(()->tell("No se pudo importar el archivo (máximo 32 MB).")); }
        },"arise-model-import").start();
    }
    private void openChat(String host) {
        LinearLayout box=new LinearLayout(this); box.setOrientation(LinearLayout.VERTICAL);
        button(box,"Volver a permisos y escucha",v->{ closeChat(); setup(); });
        chat=CompanionView.create(this,host); box.addView(chat,new LinearLayout.LayoutParams(-1,0,1)); setContentView(box);
    }
    private void closeChat() { if(chat!=null) { chat.destroy(); chat=null; } }
    @Override public void onBackPressed() { if(chat!=null) { closeChat(); setup(); } else super.onBackPressed(); }
    @Override protected void onResume() { super.onResume(); foreground=true; ui.post(refresh); }
    @Override protected void onPause() { foreground=false; ui.removeCallbacks(refresh); super.onPause(); }
    @Override protected void onDestroy() { closeChat(); super.onDestroy(); }
    private void tell(String value) { Toast.makeText(this,value,Toast.LENGTH_LONG).show(); }
    private TextView label(LinearLayout box,String value,int size) { TextView t=new TextView(this);t.setText(value);t.setTextSize(size);t.setPadding(0,12,0,12);box.addView(t);return t; }
    private EditText field(LinearLayout box,String hint,boolean secret) { EditText e=new EditText(this);e.setHint(hint);e.setSingleLine(); if(secret)e.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD); box.addView(e);return e; }
    private void button(LinearLayout box,String text,View.OnClickListener click) { Button b=new Button(this);b.setText(text);b.setOnClickListener(click);box.addView(b,new LinearLayout.LayoutParams(-1,-2)); }
}
