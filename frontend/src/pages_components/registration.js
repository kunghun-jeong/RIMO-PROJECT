import React from 'react'
import { useState } from 'react';
import Usermodal from '../modals_components/usermodal';
import Devicemodal from '../modals_components/devicemodal';
import NaturalModal from '../modals_components/naturalmodal';
import Locationmodal from '../modals_components/locationmodal';
import Urlmodal from '../modals_components/urlmodal';
import YoloModal from '../modals_components/yolomodal';
import './registration.css'



export default function Registration(props) {

  // variables for user group modal
  const [openModal, setOpenModal] = useState(false);
  
  // variables for device group modal
  const [openDeviceModal, setOpenDeviceModal] = useState(false)

  // variables for the location group modal
  const [openLocationModal, setOpenLocationModal] = useState(false)

  // variables for the URL group modal
  const [openUrlModal, setOpenUrlModal] = useState(false)

  // variables for natural language intent modal
const [openNaturalModal, setOpenNaturalModal] = useState(false);
const [openYoloModal, setOpenYoloModal] = useState(false);
  

  return (
    <div className='registration'>

        <button className={props.mode === 'dark' ? 'dark-button' : 'light-button'} style={{marginTop:"100px"}} onClick={() => {setOpenModal(true);}}>Application-Intent</button>
        {openModal && <Usermodal closeModal={setOpenModal} mode={props.mode}/>} 

        <button className={props.mode === 'dark' ? 'dark-button' : 'light-button'} onClick={() => {setOpenDeviceModal(true);}}>Network-Intent</button>
        {openDeviceModal && <Devicemodal closeDeviceModal={setOpenDeviceModal} mode={props.mode}/>}

        {/* <button className={props.mode === 'dark' ? 'dark-button' : 'light-button'}  onClick={() => {setOpenLocationModal(true);}}>Location Groups</button>
        {openLocationModal && <Locationmodal closeLocationModal={setOpenLocationModal} mode={props.mode}/>}

        <button className={props.mode === 'dark' ? 'dark-button' : 'light-button'} onClick={() => {setOpenUrlModal(true);}}>URL Groups</button>
        {openUrlModal && <Urlmodal closeUrlModal={setOpenUrlModal} mode={props.mode}/>}
         */}

         <button className={props.mode === 'dark' ? 'dark-button' : 'light-button'}  onClick={() => { setOpenNaturalModal(true); }}> Natural-Intent </button>
         {openNaturalModal &&  <NaturalModal closeNaturalModal={setOpenNaturalModal}mode={props.mode} />}

         <button className={props.mode === 'dark' ? 'dark-button' : 'light-button'} onClick={() => { setOpenYoloModal(true); }}> YOLO 자율회피 </button>
         {openYoloModal && <YoloModal closeModal={setOpenYoloModal} mode={props.mode} />}
    </div>
  )
}
