window.dash_clientside = Object.assign({}, window.dash_clientside, {
   Cesium: {
      startup_cesium: async function(id, config) {

         const configJSON = JSON.parse(config);
         const token = configJSON["cesium_token"];
         const localServer = configJSON["local_server"];

         async function checkToken(token) {
            const assetId = "2";

            try
            {
               const response = await fetch(`https://api.cesium.com/v1/assets/${assetId}/endpoint`, 
                  {
                     method: 'GET',
                     headers: {
                        'Authorization': `Bearer ${token}`
                     }
                  }
               );

               return response.status;
            }
            catch (error) {

               return error.message;
            }
         }

         function setArrowHoverEvent(viewer)
         {
            const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas); 
            let pickedEntity = null; // Store the currently picked entity

            handler.setInputAction(function (movement) {
               const pick = viewer.scene.pick(movement.endPosition);

               if (Cesium.defined(pick) && Cesium.defined(pick.id) && pick.id.polyline !== undefined && pick.id !== pickedEntity) {

                  pickedEntity = pick.id;

                  // Display description
                  const tooltip = document.getElementById('tooltip'); 
                  tooltip.style.left = movement.endPosition.x + 'px'; 
                  tooltip.style.top = movement.endPosition.y + 'px'; 
                  tooltip.style.display = 'block'; 
                  tooltip.innerHTML = pickedEntity.description; 
               } else if (!Cesium.defined(pick) && pickedEntity) {
                  // Mouse moved away from the entity
                  pickedEntity = null; 

                  // Hide description
                  const tooltip = document.getElementById('tooltip'); 
                  tooltip.style.display = 'none'; 
               }
            }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);
         }

         function setPointHoverEvent(viewer)
         {
            const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas); 
            let pickedEntity = null; // Store the currently picked entity
            let oldColor = null; // Store the original color of the picked entity


            handler.setInputAction(function (movement) {
               const pick = viewer.scene.pick(movement.endPosition);

               if (Cesium.defined(pick) && Cesium.defined(pick.id) && pick.id.point !== undefined && pick.id !== pickedEntity) {

                  // New entity hovered
                  if (pickedEntity) {
                     // Restore color of previously hovered entity
                     pickedEntity.point.color = oldColor;
                  }

                  pickedEntity = pick.id;
                  oldColor = pickedEntity.point.color.getValue(); 
                  pickedEntity.point.color = Cesium.Color.YELLOW; 

                  // Display description
                  const tooltip = document.getElementById('tooltip'); 
                  tooltip.style.left = movement.endPosition.x + 'px'; 
                  tooltip.style.top = movement.endPosition.y + 'px'; 
                  tooltip.style.display = 'block'; 
                  tooltip.innerHTML = pickedEntity.description; 
               } else if (!Cesium.defined(pick) && pickedEntity) {
                  // Mouse moved away from the entity
                  pickedEntity.point.color = oldColor; // Restore original color
                  pickedEntity = null; 

                  // Hide description
                  const tooltip = document.getElementById('tooltip'); 
                  tooltip.style.display = 'none'; 
               }
            }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);
         }

         let viewer_initializer = (async () => {

            const response = await checkToken(token);

            if (response === 200)
            {
               Cesium.Ion.defaultAccessToken = token; 
            }

            const viewer = new Cesium.Viewer(id, 
               {
                  baseLayerPicker: false,
                  geocoder: false,
                  fullscreenButton: false,
                  timeline: false,
                  sceneModePicker: false,
                  animation: false,
               }
            );

            if (response === "Failed to fetch" || response === 401)
            {
               const world_jpg = `${localServer}world`;
               const imageryLayer = new Cesium.ImageryLayer(
                  new Cesium.SingleTileImageryProvider({
                     url: world_jpg
                  })
               );
               viewer.imageryLayers.add(imageryLayer);
            }

            setPointHoverEvent(viewer);
            setArrowHoverEvent(viewer);

            return viewer;
         });

         return await viewer_initializer();
      },

      external_transmissions: function(data, cesium_viewer) {

         cesium_viewer.dataSources.removeAll();
         cesium_viewer.entities.removeAll();

         let createPoints = function(info, transmission_info, cesium_viewer) {
            const indices = Object.keys(info["Sender_Name"]);

            const sender_name = info["Sender_Name"][indices[0]];
            const sender_X = info["SenderLocation_X"][indices[0]];
            const sender_Y = info["SenderLocation_Y"][indices[0]];
            const sender_Z = info["SenderLocation_Z"][indices[0]];
            const sender_position = new Cesium.Cartesian3(sender_X, sender_Y, sender_Z);

            const receiver_name = info["Receiver_Name"][indices[0]];
            const receiver_X = info["ReceiverLocation_X"][indices[0]];
            const receiver_Y = info["ReceiverLocation_Y"][indices[0]];
            const receiver_Z = info["ReceiverLocation_Z"][indices[0]];
            const receiver_position = new Cesium.Cartesian3(receiver_X, receiver_Y, receiver_Z);

            try {
               cesium_viewer.entities.add({
                  position: sender_position,
                  point: {
                     pixelSize: 10,
                     color: transmission_info["color"],
                  },
                  id: sender_name,
                  description: transmission_info["transmission_info"]
               });
            }
            catch (error) {
               console.log(error);
            }

            try {
               cesium_viewer.entities.add({
                  position: receiver_position,
                  point: {
                     pixelSize: 10,
                     color: transmission_info["color"],
                  },
                  id: receiver_name,
                  description: transmission_info["transmission_info"]
               });
            }
            catch (error) {
               console.log(error);
            }
         }

         let createLine = function(line_data, transmission_info, cesium_viewer) {

            let x = line_data["x"];
            let y = line_data["y"];
            let z = line_data["z"];
            for (let i = 0; i < x.length - 1; i++) {
               try {
                  cesium_viewer.entities.add({
                     polyline: {
                        positions: [
                           new Cesium.Cartesian3(x[i], y[i], z[i]), 
                           new Cesium.Cartesian3(x[i+1], y[i+1], z[i+1])],
                        width: 20,
                        material: new Cesium.PolylineArrowMaterialProperty(transmission_info["color"])
                     },
                     description: transmission_info["transmission_info"]
                  });
               }
               catch (error) {
                  console.log(error);
               }
            }
         }

         let transmissionText = function(transmission, current_time, info)
         {
            let transmission_color = {
               "Success": Cesium.Color.MEDIUMTURQUOISE,
               "Fail": Cesium.Color.DARKRED
            };

            const indices = Object.keys(info["Sender_Name"]);
            const [sender, sender_part, receiver, receiver_part] = transmission

            let transmission_result = "Success";
            let transmission_num = 0;
            let transmission_info = '';
            transmission_info = `Time (H:M:S): ${current_time}<br>`;
            transmission_info += `Sender: ${sender} >> Receiver: ${receiver}<br>`;
            for (let i = 0; i < indices.length; i++)
            {
               transmission_num += 1;
               transmission_info += `
               <b>${transmission_num}. Event Type: ${info["Event_Type"][indices[i]]}</b><br>
               &nbsp;&nbsp;&nbsp;&nbsp;Platform Parts: ${sender_part} >> ${receiver_part}<br>
               &nbsp;&nbsp;&nbsp;&nbsp;Message Type: ${info["Message_Type"][indices[i]]}<br>
               &nbsp;&nbsp;&nbsp;&nbsp;Message Number: ${info["Message_SerialNumber"][indices[i]]}<br>
               &nbsp;&nbsp;&nbsp;&nbsp;Message Originator: ${info["Message_Originator"][indices[i]]}<br>`
               if (info["CommInteraction_FailedStatus"][indices[i]] !== "Does Not Exist")
               {
                  transmission_info += `&nbsp;&nbsp;&nbsp;&nbsp;Failure Reason: ${info["CommInteraction_FailedStatus"][indices[i]]}<br>`
                  transmission_result = "Fail;"
               }
            }

            result = {
               "transmission_info": transmission_info, 
               "color": transmission_color[transmission_result]
            };

            return result;
         }

         const jsonData = JSON.parse(data);
         for (const group in jsonData) {
            const transmission = jsonData[group]["transmission"];
            const info = jsonData[group]["info"];
            const line_data = jsonData[group]["line_points"];
            const current_time = jsonData[group]["current_time"];
            
            let transmission_info = transmissionText(transmission, current_time, info);
            createPoints(info, transmission_info, cesium_viewer);
            createLine(line_data, transmission_info, cesium_viewer);
         }
      },

      internal_transmissions: function(data, cesium_viewer) {

         let createPoint = function(info, transmission_info, cesium_viewer) {
            const indices = Object.keys(info["Sender_Name"]);

            const sender_name = info["Sender_Name"][indices[0]];
            const sender_X = info["SenderLocation_X"][indices[0]];
            const sender_Y = info["SenderLocation_Y"][indices[0]];
            const sender_Z = info["SenderLocation_Z"][indices[0]];
            const sender_position = new Cesium.Cartesian3(sender_X, sender_Y, sender_Z);

            try {
               cesium_viewer.entities.add({
                  position: sender_position,
                  point: {
                     pixelSize: 10,
                     color: Cesium.Color.RED,
                  },
                  id: `${sender_name}_internal`,
                  description: transmission_info
               });
            }
            catch (error) {
               console.log(error);
            }
         }

         let internalTransmissionText = function(platform, current_time, info)
         {         
            const indices = Object.keys(info["Sender_Name"]);

            let transmission_num = 0;
            let transmission_info = '';
            transmission_info = `Time (H:M:S): ${current_time}<br>`;
            transmission_info += `Platform: ${platform}<br>`; 
            for (let i = 0; i < indices.length; i++)
            {
               transmission_num += 1;
               transmission_info += `
               <b>${transmission_num}. Event Type: ${info["Event_Type"][indices[i]]}</b><br>
               &nbsp;&nbsp;&nbsp;&nbsp;Platform Parts: ${info["SenderPart_Name"][indices[i]]} >> ${info["ReceiverPart_Name"][indices[i]]}<br>
               &nbsp;&nbsp;&nbsp;&nbsp;Message Type: ${info["Message_Type"][indices[i]]}<br>
               &nbsp;&nbsp;&nbsp;&nbsp;Message Number: ${info["Message_SerialNumber"][indices[i]]}<br>
               &nbsp;&nbsp;&nbsp;&nbsp;Message Originator: ${info["Message_Originator"][indices[i]]}<br>`
            }

            return transmission_info;
         }

         const jsonData = JSON.parse(data);
         for (const platform in jsonData) {
            const info = jsonData[platform]["info"];
            const current_time = jsonData[platform]["current_time"];
            
            let transmission_info = internalTransmissionText(platform, current_time, info);
            createPoint(info, transmission_info, cesium_viewer);
         }
      },

      camera_view: function(camera_location, cesium_viewer) {

         const jsonCamera = JSON.parse(camera_location);
         let adjustCamera = function(camera_location, cesium_viewer) {

            cesium_viewer.camera.flyTo({
               destination: new Cesium.Cartesian3(
                  camera_location.x, 
                  camera_location.y, 
                  camera_location.z),
               duration: 1
            });
         }

         adjustCamera(jsonCamera, cesium_viewer);
      }
   }
});