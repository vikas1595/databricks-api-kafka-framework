[
  {
    "name": "Get_API_Config",
    "type": "Lookup",
    "dependsOn": [],
    "policy": {
      "timeout": "0.12:00:00",
      "retry": 0,
      "retryIntervalInSeconds": 30,
      "secureOutput": false,
      "secureInput": false
    },
    "userProperties": [],
    "typeProperties": {
      "source": {
        "type": "JsonSource",
        "storeSettings": {
          "type": "AzureBlobStorageReadSettings",
          "recursive": true,
          "enablePartitionDiscovery": false
        },
        "formatSettings": {
          "type": "JsonReadSettings"
        }
      },
      "dataset": {
        "referenceName": "${config_dataset_name}",
        "type": "DatasetReference"
      },
      "firstRowOnly": false
    }
  },
  {
    "name": "Process_Each_API",
    "type": "ForEach",
    "dependsOn": [
      {
        "activity": "Get_API_Config",
        "dependencyConditions": ["Succeeded"]
      }
    ],
    "userProperties": [],
    "typeProperties": {
      "items": {
        "value": "@activity('Get_API_Config').output.value",
        "type": "Expression"
      },
      "isSequential": true,
      "activities": [
        {
          "name": "Copy_API_Data",
          "type": "Copy",
          "dependsOn": [],
          "policy": {
            "timeout": "0.12:00:00",
            "retry": 0,
            "retryIntervalInSeconds": 30,
            "secureOutput": false,
            "secureInput": false
          },
          "userProperties": [],
          "typeProperties": {
            "source": {
              "type": "RestSource",
              "httpRequestTimeout": "00:01:40",
              "requestInterval": "00.00:00:00.010"
            },
            "sink": {
              "type": "JsonSink",
              "storeSettings": {
                "type": "AzureBlobStorageWriteSettings"
              },
              "formatSettings": {
                "type": "JsonWriteSettings"
              }
            },
            "enableStaging": false
          },
          "inputs": [
            {
              "referenceName": "${rest_dataset_name}",
              "type": "DatasetReference",
              "parameters": {
                "base_url": {
                  "value": "@item().base_url",
                  "type": "Expression"
                },
                "relative_url": {
                  "value": "@item().relative_url",
                  "type": "Expression"
                }
              }
            }
          ],
          "outputs": [
            {
              "referenceName": "${sink_dataset_name}",
              "type": "DatasetReference",
              "parameters": {
                "FileName": {
                  "value": "@item().destination.file_name",
                  "type": "Expression"
                },
                "FolderPath": {
                  "value": "@item().destination.path",
                  "type": "Expression"
                }
              }
            }
          ]
        }
      ]
    }
  }
]
