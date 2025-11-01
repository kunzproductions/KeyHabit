-- Max_Module.ms - KeyHabit Sync for 3ds Max
-- Two-way sync: Import from Blender (info.json) & Export to Blender (request.json)

-- ================ CONFIG ================
global SYNC_FOLDER = "C:\\KeyHabit_Sync\\"
global INFO_JSON_PATH = SYNC_FOLDER + "info.json"
global REQUEST_JSON_PATH = SYNC_FOLDER + "request.json"
global FBX_PATH = SYNC_FOLDER + "KHB_Sync.fbx"

-- ================ GLOBAL STATE ================
global khb_sync_running = false
global khb_timer_active = false

-- ================ UTILITY FUNCTIONS ================

fn logMessage msg = (
    format "[KeyHabit] %\n" msg
)

fn showSyncStatus msg duration:3000 = (
    -- Hiển thị message trong viewport
    messageBox msg title:"KeyHabit Sync" beep:false
)

-- ================ JSON UTILITIES ================

fn parseSimpleJSON jsonString = (
    /*
    Parse simple JSON format (for request.json)
    Returns dictionary with keys
    */
    local result = #()
    
    -- Remove brackets and whitespace
    local cleaned = substituteString jsonString "{" ""
    cleaned = substituteString cleaned "}" ""
    cleaned = substituteString cleaned "[" ""
    cleaned = substituteString cleaned "]" ""
    cleaned = substituteString cleaned "\"" ""
    
    -- Split by comma
    local pairs = filterString cleaned ","
    
    for pair in pairs do (
        local keyValue = filterString pair ":"
        if keyValue.count == 2 then (
            local key = trimLeft (trimRight keyValue[1])
            local value = trimLeft (trimRight keyValue[2])
            append result #(key, value)
        )
    )
    
    return result
)

fn getValueFromJSON jsonData key = (
    /*
    Get value from parsed JSON by key
    */
    for pair in jsonData do (
        if pair[1] == key then (
            return pair[2]
        )
    )
    return undefined
)

fn createSimpleJSON collection timestamp = (
    /*
    Create simple JSON string for info.json
    */
    local jsonStr = "[\n"
    jsonStr += "  {\"t\": \"" + timestamp + "\"},\n"
    jsonStr += "  {\n"
    jsonStr += "    \"collection\": \"" + collection + "\",\n"
    jsonStr += "    \"path\": \"" + FBX_PATH + "\"\n"
    jsonStr += "  }\n"
    jsonStr += "]"
    return jsonStr
)

-- ================ FILE OPERATIONS ================

fn checkFileExists filePath = (
    doesFileExist filePath
)

fn deleteFile filePath = (
    try (
        if doesFileExist filePath then (
            deleteFile filePath
            return true
        )
        return false
    ) catch (
        logMessage ("Lỗi xóa file: " + filePath)
        return false
    )
)

fn readTextFile filePath = (
    try (
        local fileStream = openFile filePath mode:"r"
        if fileStream != undefined then (
            local content = ""
            while not eof fileStream do (
                content += readLine fileStream + "\n"
            )
            close fileStream
            return #(true, content)
        )
        return #(false, "Cannot open file")
    ) catch (
        return #(false, "Error reading file")
    )
)

fn writeTextFile filePath content = (
    try (
        local fileStream = createFile filePath
        if fileStream != undefined then (
            format content to:fileStream
            close fileStream
            return true
        )
        return false
    ) catch (
        logMessage ("Lỗi ghi file: " + filePath)
        return false
    )
)

-- ================ IMPORT FROM BLENDER (info.json) ================

fn checkSyncFiles = (
    if not (checkFileExists INFO_JSON_PATH) then (
        return #(false, "File info.json không tồn tại")
    )
    if not (checkFileExists FBX_PATH) then (
        return #(false, "File FBX không tồn tại")
    )
    return #(true, "Files tồn tại")
)

fn deleteExistingGroup groupName = (
    try (
        local groupObj = getNodeByName groupName
        if groupObj != undefined then (
            delete groupObj
        )
        return true
    ) catch (
        logMessage ("Lỗi xóa group: " + groupName)
        return false
    )
)

fn importFBX fbxPath = (
    try (
        importFile fbxPath #noPrompt
        logMessage ("Import FBX: " + fbxPath)
        return true
    ) catch (
        logMessage ("Lỗi import FBX: " + fbxPath)
        return false
    )
)

fn groupImportedObjects groupName = (
    try (
        -- Select all imported objects
        local importedObjs = $* as array
        
        if importedObjs.count > 0 then (
            -- Create group
            local newGroup = group importedObjs name:groupName
            logMessage ("Đã group " + importedObjs.count as string + " objects")
            return true
        )
        return false
    ) catch (
        logMessage "Lỗi group objects"
        return false
    )
)

fn applySmoothToObject obj = (
    try (
        -- Add TurboSmooth modifier
        local turboSmooth = TurboSmooth()
        turboSmooth.iterations = 2
        addModifier obj turboSmooth
        return true
    ) catch (
        return false
    )
)

fn importFromBlender = (
    /*
    Import từ Blender khi phát hiện info.json
    */
    local filesExist = checkSyncFiles()
    if not filesExist[1] then (
        return true  -- Không có file để import
    )
    
    -- Read info.json (simplified)
    local readResult = readTextFile INFO_JSON_PATH
    if not readResult[1] then (
        logMessage "Lỗi đọc info.json"
        return false
    )
    
    local jsonContent = readResult[2]
    logMessage "Import từ Blender..."
    
    try (
        -- Parse collection name (simplified)
        local collectionName = "ImportedCollection"
        
        -- Delete old group
        deleteExistingGroup collectionName
        
        -- Import FBX
        local success = importFBX FBX_PATH
        if not success then (
            return false
        )
        
        -- Group objects
        groupImportedObjects collectionName
        
        -- Delete info.json
        deleteFile INFO_JSON_PATH
        
        logMessage "✓ Import completed"
        showSyncStatus "Import OK"
        return true
        
    ) catch (
        logMessage "Lỗi import"
        return false
    )
)

-- ================ EXPORT TO BLENDER (request.json) ================

fn checkRequestFile = (
    checkFileExists REQUEST_JSON_PATH
)

fn readRequestJSON = (
    /*
    Đọc request.json và parse collection name
    */
    local readResult = readTextFile REQUEST_JSON_PATH
    if readResult[1] then (
        local jsonData = parseSimpleJSON readResult[2]
        local collectionName = getValueFromJSON jsonData "collection"
        return #(true, collectionName)
    )
    return #(false, undefined)
)

fn backupUVChannels obj = (
    /*
    Backup tất cả UV channels của object
    Returns: array of #(channel, uvData)
    */
    local backup = #()
    local numMaps = polyOp.getNumMaps obj
    
    for ch = 1 to numMaps do (
        if polyOp.getMapSupport obj ch then (
            local uvVerts = #()
            local vertCount = polyOp.getNumMapVerts obj ch
            
            for v = 1 to vertCount do (
                append uvVerts (polyOp.getMapVert obj ch v)
            )
            
            append backup #(ch, uvVerts)
        )
    )
    
    return backup
)

fn restoreUVChannels obj uvBackup = (
    /*
    Restore UV channels từ backup
    */
    try (
        for entry in uvBackup do (
            local channel = entry[1]
            local uvData = entry[2]
            
            polyOp.setMapSupport obj channel true
            
            for i = 1 to uvData.count do (
                polyOp.setMapVert obj channel i uvData[i]
            )
        )
        logMessage ("Restored UV channels for " + obj.name)
        return true
    ) catch (
        logMessage "Lỗi restore UV"
        return false
    )
)

fn convertSmoothingGroupsToUDIM obj = (
    /*
    Convert smoothing groups thành UDIM tiles
    Smoothing Group 1 → UDIM 1001
    Smoothing Group 2 → UDIM 1002
    ...
    */
    try (
        -- Convert to Editable Poly nếu cần
        if classOf obj != Editable_Poly then (
            convertToPoly obj
        )
        
        -- Get face count
        local faceCount = polyOp.getNumFaces obj
        
        -- Collect unique smoothing groups
        local smoothingGroups = #()
        for f = 1 to faceCount do (
            local sg = polyOp.getFaceSmoothGroup obj f
            if sg != 0 and (findItem smoothingGroups sg) == 0 then (
                append smoothingGroups sg
            )
        )
        
        logMessage (smoothingGroups.count as string + " smoothing groups found")
        
        -- Create new UV channel (channel 2 for KHB_smooth_group)
        polyOp.setNumMaps obj 3
        
        -- Unwrap each smoothing group to UDIM tile
        for i = 1 to smoothingGroups.count do (
            local sgID = smoothingGroups[i]
            local udimTile = 1001 + (i - 1)  -- UDIM offset
            
            -- Select faces with this smoothing group
            local sgFaces = #()
            for f = 1 to faceCount do (
                if (polyOp.getFaceSmoothGroup obj f) == sgID then (
                    append sgFaces f
                )
            )
            
            -- Unwrap to UDIM tile (channel 2)
            if sgFaces.count > 0 then (
                -- Simplified: Offset UVs
                local uOffset = (udimTile - 1001)
                
                for faceIdx in sgFaces do (
                    local faceVerts = polyOp.getFaceVerts obj faceIdx
                    
                    for v in faceVerts do (
                        local uvw = polyOp.getMapVert obj 2 v
                        uvw.x += uOffset
                        polyOp.setMapVert obj 2 v uvw
                    )
                )
            )
        )
        
        logMessage "Converted smoothing groups to UDIM"
        return true
        
    ) catch (
        logMessage "Lỗi convert smoothing groups"
        return false
    )
)

fn exportCollectionToBlender collectionName = (
    /*
    Export collection/group về Blender với Smoothing Groups → UDIM
    CHỈ EXPORT CHILDREN, KHÔNG EXPORT GROUP
    */
    try (
        -- Find group by name
        local groupObj = getNodeByName collectionName
        if groupObj == undefined then (
            logMessage ("Collection '" + collectionName + "' không tồn tại")
            return false
        )
        
        logMessage ("Exporting collection: " + collectionName)
        
        -- Get CHILDREN của group (không export group itself)
        local objsToExport = #()
        for obj in groupObj.children do (
            -- Chỉ lấy mesh objects
            if (classOf obj == Editable_Poly) or (classOf obj == Editable_Mesh) or (superClassOf obj == GeometryClass) then (
                append objsToExport obj
            )
        )
        
        if objsToExport.count == 0 then (
            logMessage "Không có mesh objects để export"
            return false
        )
        
        -- Process Smoothing Groups cho mỗi mesh
        local uvBackups = #()
        
        for obj in objsToExport do (
            if (classOf obj == Editable_Poly) or (classOf obj == Editable_Mesh) then (
                -- Backup UV channels
                local backup = backupUVChannels obj
                append uvBackups #(obj, backup)
                
                -- Convert Smoothing Groups → UDIM
                convertSmoothingGroupsToUDIM obj
            )
        )
        
        -- Export FBX - CHỈ EXPORT OBJECTS, KHÔNG EXPORT GROUP
        select objsToExport
        exportFile FBX_PATH #noPrompt selectedOnly:true using:FBXEXP
        logMessage ("Exported " + objsToExport.count as string + " objects")
        
        -- Create info.json
        local timestamp = localTime as string
        local jsonContent = createSimpleJSON collectionName timestamp
        writeTextFile INFO_JSON_PATH jsonContent
        logMessage "Created info.json"
        
        -- RESTORE: Khôi phục lại UV channels
        for entry in uvBackups do (
            local obj = entry[1]
            local backup = entry[2]
            restoreUVChannels obj backup
        )
        
        logMessage ("✓ Exported '" + collectionName + "' to Blender")
        showSyncStatus ("Exported: " + collectionName)
        return true
        
    ) catch (
        logMessage "Lỗi export"
        return false
    )
)

fn handleExportRequest = (
    /*
    Xử lý request export từ Blender
    */
    if not (checkRequestFile()) then (
        return true
    )
    
    local readResult = readRequestJSON()
    if not readResult[1] then (
        logMessage "Lỗi đọc request.json"
        deleteFile REQUEST_JSON_PATH
        return false
    )
    
    local collectionName = readResult[2]
    if collectionName == undefined then (
        logMessage "Request không có collection name"
        deleteFile REQUEST_JSON_PATH
        return false
    )
    
    logMessage ("Blender request export: " + collectionName)
    
    -- Export collection
    local success = exportCollectionToBlender collectionName
    
    -- Delete request file
    deleteFile REQUEST_JSON_PATH
    
    return success
)

-- ================ SYNC LOOP ================

fn checkSyncPeriodically = (
    /*
    Kiểm tra file sync định kỳ
    */
    if not khb_sync_running then (
        return false
    )
    
    -- Check import (info.json từ Blender)
    importFromBlender()
    
    -- Check export request (request.json từ Blender)
    handleExportRequest()
    
    return true
)

fn startSyncScript = (
    /*
    Bắt đầu script sync
    */
    khb_sync_running = true
    logMessage "Sync: ON"
    showSyncStatus "KeyHabit Sync: ACTIVE"
    
    -- Check ngay lập tức
    importFromBlender()
    handleExportRequest()
    
    -- Setup timer (check mỗi 1 giây)
    if not khb_timer_active then (
        khb_timer_active = true
        -- 3ds Max timer callback
        callbacks.addScript #filePostOpen "checkSyncPeriodically()" id:#khb_sync
    )
)

fn stopSyncScript = (
    /*
    Dừng script sync
    */
    khb_sync_running = false
    khb_timer_active = false
    
    -- Remove callbacks
    callbacks.removeScripts #filePostOpen id:#khb_sync
    
    logMessage "Sync: OFF"
    showSyncStatus "KeyHabit Sync: STOPPED"
)

fn toggleSyncScript = (
    /*
    Toggle script - chạy lần đầu để bật, chạy lần nữa để tắt
    */
    if not khb_sync_running then (
        startSyncScript()
    ) else (
        stopSyncScript()
    )
)

-- ================ EXECUTION ================

-- Chạy toggle khi load script
toggleSyncScript()

logMessage "KeyHabit Sync for 3ds Max loaded. Run 'toggleSyncScript()' to start/stop."

