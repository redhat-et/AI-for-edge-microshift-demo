#include <WebServer.h>
#include <WiFi.h>
#include <esp32cam.h>
#include <esp_camera.h>
#include <wifi_pass.h>
#include <ESPmDNS.h>
#include <HTTPClient.h>

WebServer server(80);
IPAddress microShiftAddress;

static auto hiRes = esp32cam::Resolution::find(640, 480);

void
handleJpgHi()
{
  pinMode(4,OUTPUT);
  digitalWrite(4,HIGH);

  delay(150);

  if (!esp32cam::Camera.changeResolution(hiRes)) {
    Serial.println("SET-HI-RES FAIL");
  }

  auto frame = esp32cam::capture();
  pinMode(4,OUTPUT);
  digitalWrite(4,LOW);

  if (frame == nullptr) {
    Serial.println("CAPTURE FAIL");
    server.send(503, "", "");
    return;
  }
  Serial.printf("CAPTURE OK %dx%d %db\n", frame->getWidth(), frame->getHeight(),
                static_cast<int>(frame->size()));

  server.setContentLength(frame->size());
  server.send(200, "image/jpeg");
  WiFiClient client = server.client();
  frame->writeTo(client);

}


bool anyoneStreaming;

void
handleMjpeg()
{
  anyoneStreaming = true;

  if (!esp32cam::Camera.changeResolution(hiRes)) {
    Serial.println("SET-HI-RES FAIL");
  }

  Serial.println("STREAM BEGIN");
  WiFiClient client = server.client();
  auto startTime = millis();
  int res = esp32cam::Camera.streamMjpeg(client);

  anyoneStreaming = false;
  //Trigger reconnection to microshift camserver
  microShiftAddress = IPAddress((uint32_t)0);

  if (res <= 0) {
    Serial.printf("STREAM ERROR %d\n", res);
    return;
  }
  auto duration = millis() - startTime;
  Serial.printf("STREAM END %dfrm %0.2ffps\n", res, 1000.0 * res / duration);
}

char token[32];

char *getCamID() {

   static char cam_id[17];
   uint32_t chipId = 0;
   for(int i=0; i<17; i=i+8) {
	  chipId |= ((ESP.getEfuseMac() >> (40 - i)) & 0xff) << i;
   }
   sprintf(cam_id,"CAM_%08x", chipId);
   return cam_id;
}
   	
void
setup()
{

  Serial.begin(115200);
  Serial.println();

  sprintf(token, "%08x", esp_random());

  char *cam_id = getCamID();
   
  if(!MDNS.begin(cam_id)) {
     Serial.println("Error starting mDNS");
     return;
  }

  Serial.print("Started mDNS server as ");
  Serial.println(cam_id);


  {
    using namespace esp32cam;
    Config cfg;
    cfg.setPins(pins::AiThinker);
    cfg.setResolution(hiRes);
    cfg.setBufferCount(2);
    cfg.setJpeg(90);

    bool ok = Camera.begin(cfg);
    Serial.println(ok ? "CAMERA OK" : "CAMERA FAIL");
 
  sensor_t * s = esp_camera_sensor_get();
  s->set_brightness(s, 0);     // -2 to 2
  s->set_contrast(s, 0);       // -2 to 2
  s->set_saturation(s, 0);     // -2 to 2
  s->set_special_effect(s, 0); // 0 to 6 (0 - No Effect, 1 - Negative, 2 - Grayscale, 3 - Red Tint, 4 - Green Tint, 5 - Blue Tint, 6 - Sepia)
  s->set_whitebal(s, 1);       // 0 = disable , 1 = enable
  s->set_awb_gain(s, 1);       // 0 = disable , 1 = enable
  s->set_wb_mode(s, 0);        // 0 to 4 - if awb_gain enabled (0 - Auto, 1 - Sunny, 2 - Cloudy, 3 - Office, 4 - Home)
  s->set_exposure_ctrl(s, 1);  // 0 = disable , 1 = enable
  s->set_aec2(s, 0);           // 0 = disable , 1 = enable
  s->set_ae_level(s, 0);       // -2 to 2
  s->set_aec_value(s, 300);    // 0 to 1200
  s->set_gain_ctrl(s, 1);      // 0 = disable , 1 = enable
  s->set_agc_gain(s, 0);       // 0 to 30
  s->set_gainceiling(s, (gainceiling_t)0);  // 0 to 6
  s->set_bpc(s, 0);            // 0 = disable , 1 = enable
  s->set_wpc(s, 1);            // 0 = disable , 1 = enable
  s->set_raw_gma(s, 1);        // 0 = disable , 1 = enable
  s->set_lenc(s, 1);           // 0 = disable , 1 = enable
  s->set_hmirror(s, 0);        // 0 = disable , 1 = enable
  s->set_vflip(s, 0);          // 0 = disable , 1 = enable
  s->set_dcw(s, 1);            // 0 = disable , 1 = enable
  s->set_colorbar(s, 0);       // 0 = disable , 1 = enable

  }

  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
 
  Serial.println("lights on!");
 

  Serial.print("http://");
  Serial.println(WiFi.localIP());
  Serial.println("  /cam-hi.jpg");

  server.on("/cam-hi.jpg", handleJpgHi);
  server.on("/stream", handleMjpeg);

  server.begin();
}

bool microShiftResolved = false;

#define HOSTNAME "microshift-cam-reg"
#define HOSTNAME_FULL HOSTNAME ".local"

void
loop()
{
  server.handleClient();

  if (!microShiftAddress) {
  	microShiftAddress = MDNS.queryHost(HOSTNAME);
        if (microShiftAddress) {
 	    Serial.print("microshift address resolved to: ");
            Serial.println(microShiftAddress.toString());
  	    if (!registerInCamServer()) {
		microShiftAddress = IPAddress((uint32_t)0);
            }        
             
        } else {
            Serial.println("Could not resolve microshift address");
            delay(1000);
        }
  }	
}

bool registerInCamServer() {

  // If you wonder why using a bare TCP client instead of the HTTPClient:
  // HTTPClient does not let you provide a hostname when contacting an
  // IP Address, and without that openshift router (or any other type
  // of http load balancer, won't know where to send the request)

  String requestPath = "/register?ip=";
  requestPath += WiFi.localIP().toString();
  requestPath += "&token=";
  requestPath += token;

  WiFiClient client;

  if (!client.connect(microShiftAddress, 80)) {
	Serial.println("Connection failed");
  }

  client.println("GET " + requestPath + " HTTP/1.1");
  client.println("Host: " HOSTNAME_FULL);
  client.println("Connection: close");
  client.println();

  Serial.println("disconnected");
  client.stop();
  return true;
}

