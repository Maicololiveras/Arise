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
    private android.webkit.ValueCallback<Uri[]> imageChoice;
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
        label(box, "Tu asistente en el teléfono. Tu PC realiza el trabajo. Conecta Tailscale y pega el enlace que muestra ARISE en el PC.", 16);
        button(box,"Abrir Tailscale",v->{
            Intent launch=getPackageManager().getLaunchIntentForPackage("com.tailscale.ipn");
            if(launch!=null)startActivity(launch);
            else startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse("https://tailscale.com/download/android")));
        });
        status = label(box, "Escucha apagada", 16);
        origin = field(box, "Pega tu enlace de vinculación", false);
        origin.setText(getSharedPreferences("wake",0).getString("origin", ""));
        button(box,"Escanear QR del PC",v->com.google.mlkit.vision.codescanner.GmsBarcodeScanning.getClient(this).startScan()
            .addOnSuccessListener(barcode->{
                String value=barcode.getRawValue();
                if(value!=null && value.length()<2048){origin.setText(value);tell("Revisa el enlace y pulsa Conectar.");}
                else tell("El QR no contiene un enlace válido.");
            }).addOnFailureListener(error->tell("No se pudo abrir el lector. Puedes pegar el enlace del PC; revisa Google Play Services.")));
        button(box, "Conectar con mi PC", v -> {
            try {
                Uri link=Uri.parse(origin.getText().toString().trim());
                String host = Origin.validate(link.buildUpon().fragment(null).build().toString());
                String fragment=link.getEncodedFragment();
                if(fragment!=null && !fragment.matches("code=[A-Za-z0-9_%=-]{1,200}"))throw new IllegalArgumentException();
                stopService(new Intent(this, WakeService.class));
                getSharedPreferences("wake",0).edit().putString("origin",host).apply();
                openChat(host);
                if(fragment!=null)chat.loadUrl(host+"/#"+fragment);
            } catch (RuntimeException e) { tell("Introduce el origen HTTPS de Tailscale, sin rutas ni puertos."); }
        });
        LinearLayout advanced=new LinearLayout(this);advanced.setOrientation(LinearLayout.VERTICAL);advanced.setVisibility(View.GONE);
        button(box,"Opciones avanzadas de escucha",v->advanced.setVisibility(advanced.getVisibility()==View.VISIBLE?View.GONE:View.VISIBLE));
        box.addView(advanced);
        button(advanced, "1 · Permitir mostrar sobre otras apps", v -> new AlertDialog.Builder(this)
                .setTitle("Burbuja sobre otras aplicaciones")
                .setMessage("Android abrirá sus ajustes. Activa el permiso de ARISE Companion QA. Puedes revocarlo allí en cualquier momento. Esto no concede control del PC ni acceso al contenido de otras apps.")
                .setNegativeButton("Ahora no",null).setPositiveButton("Abrir ajustes",(d,w)-> {
                    try { startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,Uri.parse("package:"+getPackageName()))); }
                    catch (ActivityNotFoundException e) { tell("Abre Ajustes > Aplicaciones > Acceso especial > Mostrar sobre otras apps."); }
                }).show());
        button(advanced, "2 · Permitir micrófono y notificaciones", v -> {
            if (Build.VERSION.SDK_INT >= 33) requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO, Manifest.permission.POST_NOTIFICATIONS},10);
            else requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},10);
        });
        label(advanced,"3 · Detector local Porcupine (opcional)\nRequiere tu AccessKey y modelos compatibles de ‘oye ARISE’ para Android y español. El SDK puede validar la licencia con Picovoice. No se incluyen clave ni modelo personalizado; consulta sus condiciones. Sin configurarlo, el chat manual sigue disponible.",16);
        accessKey = field(advanced,"AccessKey de Picovoice (no se muestra al volver)",true);
        button(advanced,"Guardar clave del detector",v->{
            try {
                String key=accessKey.getText().toString().trim();
                if(key.isEmpty()) { tell("Introduce una clave."); return; }
                stopService(new Intent(this,WakeService.class)); KeyStoreSecret.save(this,key); accessKey.setText(""); tell("Clave guardada con Android Keystore.");
            } catch(Exception e) { tell("No se pudo guardar la clave. No se activó la escucha."); }
        });
        button(advanced,"Importar ‘oye ARISE’ Android (.ppn)",v->pick(20));
        button(advanced,"Importar modelo de español (.pv)",v->pick(21));
        button(advanced,"Activar escucha de ‘oye ARISE’",v->startWake());
        button(advanced,"Apagar micrófono y quitar burbuja",v->{ stopService(new Intent(this,WakeService.class)); tell("Escucha apagada. Las tareas del PC se detienen desde el chat."); });
        button(advanced,"Borrar clave y modelos locales",v->new AlertDialog.Builder(this).setMessage("Se apagará la escucha y se borrará la configuración del detector. La vinculación del PC se revoca por separado en ARISE.")
                .setNegativeButton("Cancelar",null).setPositiveButton("Borrar",(d,w)->{
                    stopService(new Intent(this,WakeService.class));
                    getSharedPreferences("wake",0).edit().remove("key").apply();
                    new File(getFilesDir(),"keyword.ppn").delete(); new File(getFilesDir(),"spanish.pv").delete(); tell("Detector eliminado.");
                }).show());
        label(advanced,"La escucha no se reinicia al encender el teléfono ni al volver a dar un permiso. Con pantalla bloqueada no mostramos conversaciones. Pruebas de batería y bloqueo pendientes en Redmi 13C.",14);
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
    void chooseImages(android.webkit.ValueCallback<Uri[]> callback) {
        if(imageChoice!=null)imageChoice.onReceiveValue(null);
        imageChoice=callback;
        try {startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("image/*").putExtra(Intent.EXTRA_MIME_TYPES,new String[]{"image/png","image/jpeg"}).putExtra(Intent.EXTRA_ALLOW_MULTIPLE,true).addCategory(Intent.CATEGORY_OPENABLE),31);}
        catch(ActivityNotFoundException error){imageChoice.onReceiveValue(null);imageChoice=null;tell("No hay selector de archivos disponible.");}
    }
    @Override protected void onActivityResult(int code,int result,Intent data) {
        super.onActivityResult(code,result,data);
        if(code==31){
            if(imageChoice!=null){
                Uri[] selected=null;
                if(result==RESULT_OK && data!=null){
                    if(data.getClipData()!=null){int count=data.getClipData().getItemCount();if(count<=4){selected=new Uri[count];for(int i=0;i<count;i++)selected[i]=data.getClipData().getItemAt(i).getUri();}else tell("Selecciona hasta cuatro imágenes.");}
                    else if(data.getData()!=null)selected=new Uri[]{data.getData()};
                }
                imageChoice.onReceiveValue(selected);imageChoice=null;
            }
            return;
        }
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
        button(box,"Conexión y ajustes",v->{ closeChat(); setup(); });
        chat=CompanionView.create(this,host); box.addView(chat,new LinearLayout.LayoutParams(-1,0,1)); setContentView(box);
    }
    private void closeChat() { if(imageChoice!=null){imageChoice.onReceiveValue(null);imageChoice=null;} if(chat!=null) { chat.destroy(); chat=null; } }
    @Override public void onBackPressed() { if(chat!=null) { closeChat(); setup(); } else super.onBackPressed(); }
    @Override protected void onResume() { super.onResume(); foreground=true; if(chat!=null)chat.onResume(); ui.post(refresh); }
    @Override protected void onPause() { foreground=false; ui.removeCallbacks(refresh); if(chat!=null){chat.evaluateJavascript("if(typeof recorder!=='undefined' && recorder)recorder.stop();if(typeof playing!=='undefined' && playing)playing.pause();",null);chat.onPause();} super.onPause(); }
    @Override protected void onDestroy() { closeChat(); super.onDestroy(); }
    private void tell(String value) { Toast.makeText(this,value,Toast.LENGTH_LONG).show(); }
    private TextView label(LinearLayout box,String value,int size) { TextView t=new TextView(this);t.setText(value);t.setTextSize(size);t.setPadding(0,12,0,12);box.addView(t);return t; }
    private EditText field(LinearLayout box,String hint,boolean secret) { EditText e=new EditText(this);e.setHint(hint);e.setSingleLine(); if(secret)e.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD); box.addView(e);return e; }
    private void button(LinearLayout box,String text,View.OnClickListener click) { Button b=new Button(this);b.setText(text);b.setOnClickListener(click);box.addView(b,new LinearLayout.LayoutParams(-1,-2)); }
}
